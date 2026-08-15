"""Resources — what tokenizers are downloaded, where they live, how big they are."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from norefund.core.resources import (
    ManagedDir,
    ResourceDownloadError,
    ResourceReport,
    TokenizerResource,
    build_resource_report,
    download_tokenizer,
)
from norefund.gui import formatting, theme
from norefund.gui.theme import COLORS
from norefund.gui.widgets import (
    IconButton,
    LoadingOverlay,
    StatPill,
    ThreadSafeSchedulerMixin,
    bind_mousewheel,
    section_label,
    status_dot,
)

_PATH_MAX_CHARS = 64


def _open_folder(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError:
        pass


class _TokenizerRow(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        resource: TokenizerResource,
        *,
        is_downloading: Callable[[str], bool],
        is_busy: Callable[[], bool],
        start_download: Callable[[TokenizerResource], None],
        cancel_download: Callable[[], None],
    ) -> None:
        super().__init__(
            parent, fg_color=COLORS["card"], corner_radius=theme.RADIUS_CARD
        )
        self._resource = resource
        self._is_downloading = is_downloading
        self._is_busy = is_busy
        self._start_download = start_download
        self._cancel_download = cancel_download

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_3)
        inner.columnconfigure(1, weight=1)

        self._status_dot = status_dot(inner)
        self._status_dot.grid(
            row=0, column=0, rowspan=2, padx=(0, theme.SPACE_3), sticky="n"
        )

        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(
            title_row,
            text=resource.name,
            font=theme.font(theme.FONT_TITLE, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text=resource.backend,
            font=theme.font(theme.FONT_MICRO, "bold"),
            fg_color=COLORS["muted"],
            text_color=COLORS["muted_fg"],
            corner_radius=8,
            padx=theme.SPACE_2,
        ).pack(side="left", padx=(theme.SPACE_2, 0))

        n_models = len(resource.model_ids)
        sub_text = f"used by {n_models} model{'s' if n_models != 1 else ''}"
        self._sub_label = ctk.CTkLabel(
            inner,
            text=sub_text,
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        )
        self._sub_label.grid(row=1, column=1, sticky="ew", pady=(theme.SPACE_1, 0))

        self._path_label = ctk.CTkLabel(
            inner,
            text="",
            font=theme.mono_font(theme.FONT_MICRO),
            text_color=COLORS["muted_fg"],
            anchor="w",
        )
        self._path_label.grid(row=2, column=1, sticky="ew", pady=(theme.SPACE_1, 0))

        self._size_label = ctk.CTkLabel(
            inner,
            text="",
            font=theme.mono_font(theme.FONT_BODY),
            text_color=COLORS["muted_fg"],
        )
        self._size_label.grid(row=0, column=2, padx=(theme.SPACE_3, theme.SPACE_3))

        self._action_area = ctk.CTkFrame(inner, fg_color="transparent")
        self._action_area.grid(row=0, column=3, rowspan=2)

        # Renders resource.notes, which is often not an error at all (e.g.
        # an auth hint with an "open page" link) -- named for its content,
        # not assumed failure state.
        self._notes_label = ctk.CTkLabel(
            inner,
            text="",
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["destructive"],
            anchor="w",
            wraplength=480,
            justify="left",
        )

        self.set_resource(resource)

    # ------------------------------------------------------------------

    def set_resource(self, resource: TokenizerResource) -> None:
        self._resource = resource
        self._status_dot.configure(
            fg_color=COLORS["primary"] if resource.is_cached else COLORS["muted_fg"]
        )
        self._size_label.configure(text=formatting.fmt_bytes(resource.size_bytes))
        if resource.cache_path is not None:
            self._path_label.configure(
                text=formatting.elide_middle(str(resource.cache_path), _PATH_MAX_CHARS)
            )
        else:
            self._path_label.configure(text="not downloaded")

        link_url = (
            resource.source_url
            if resource.notes and resource.backend == "hf" and resource.source_url
            else None
        )
        if resource.notes:
            text = resource.notes
            if link_url:
                text += "  open page"
            self._notes_label.configure(
                text=text,
                image=(
                    theme.icon_image(
                        "external_link", size=12, color=COLORS["destructive"]
                    )
                    if link_url
                    else theme.blank_icon(size=12)
                ),
                compound="right",
            )
            self._notes_label.grid(
                row=3, column=1, columnspan=3, sticky="ew", pady=(theme.SPACE_1, 0)
            )
            if link_url:
                self._notes_label.configure(cursor="hand2")
                self._notes_label.bind(
                    "<Button-1>", lambda _e, url=link_url: webbrowser.open(url)
                )
            else:
                self._notes_label.configure(cursor="")
                self._notes_label.unbind("<Button-1>")
        else:
            self._notes_label.grid_forget()

        self.refresh_action()

    def refresh_action(self) -> None:
        for child in self._action_area.winfo_children():
            child.destroy()

        if self._resource.is_cached:
            IconButton(
                self._action_area,
                "Open folder",
                icon="folder_open",
                command=self._open_folder,
            ).pack(side="left")
            return

        if self._is_downloading(self._resource.key):
            self._progress = ctk.CTkProgressBar(
                self._action_area,
                width=120,
                progress_color=COLORS["primary"],
                fg_color=COLORS["muted"],
            )
            self._progress.pack(side="left", padx=(0, theme.SPACE_2))
            self._progress.set(0)
            IconButton(
                self._action_area,
                "Cancel",
                icon="x",
                variant="danger",
                command=self._cancel_download,
            ).pack(side="left")
            return

        can_download = self._resource.source_url is not None
        IconButton(
            self._action_area,
            "Download",
            icon="download",
            variant="primary",
            command=lambda: self._start_download(self._resource),
            state="normal" if can_download and not self._is_busy() else "disabled",
        ).pack(side="left")

    def set_progress(self, downloaded: int, total: int | None) -> None:
        if not hasattr(self, "_progress") or not self._progress.winfo_exists():
            return
        if total:
            self._progress.configure(mode="determinate")
            self._progress.set(min(1.0, downloaded / total))
        else:
            self._progress.configure(mode="indeterminate")
            self._progress.start()

    def _open_folder(self) -> None:
        if self._resource.cache_path is not None:
            _open_folder(self._resource.cache_path.parent)


class _DirRow(ctk.CTkFrame):
    def __init__(self, parent, managed_dir: ManagedDir) -> None:
        super().__init__(
            parent, fg_color=COLORS["card"], corner_radius=theme.RADIUS_CARD
        )
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_3)
        inner.columnconfigure(0, weight=1)

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            left,
            text=managed_dir.label,
            font=theme.font(theme.FONT_LABEL, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            left,
            text=formatting.elide_middle(str(managed_dir.path), _PATH_MAX_CHARS),
            font=theme.mono_font(theme.FONT_MICRO),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(theme.SPACE_1, 0))

        ctk.CTkLabel(
            inner,
            text=(
                f"{formatting.fmt_bytes(managed_dir.size_bytes)}"
                f"  ·  {managed_dir.file_count} file"
                f"{'s' if managed_dir.file_count != 1 else ''}"
            ),
            font=theme.mono_font(theme.FONT_BODY),
            text_color=COLORS["muted_fg"],
        ).grid(row=0, column=1, padx=theme.SPACE_3)

        IconButton(
            inner,
            "Open folder",
            icon="folder_open",
            command=lambda: _open_folder(managed_dir.path),
            state="normal" if managed_dir.exists else "disabled",
        ).grid(row=0, column=2)


class ResourcesView(ThreadSafeSchedulerMixin, ctk.CTkFrame):
    def __init__(self, parent, shell) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell
        self._report: ResourceReport | None = None
        self._rows: dict[str, _TokenizerRow] = {}
        self._loading = False
        self._downloading_key: str | None = None
        self._cancel_event: threading.Event | None = None
        self._download_queue: list[str] = []

        self._build_header()
        self._build_scroll()
        self._refresh()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(
            fill="x", padx=theme.PAGE_GUTTER, pady=(theme.SPACE_5, theme.SPACE_3)
        )

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            left,
            text="Resources",
            font=theme.font(theme.FONT_HEADING, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            left,
            text="Tokenizers downloaded to this machine, and where they live on disk.",
            font=theme.font(theme.FONT_BODY),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(theme.SPACE_1, 0))

        stats_row = ctk.CTkFrame(header, fg_color="transparent")
        stats_row.pack(side="left", padx=theme.SPACE_7)
        self._downloaded_pill = StatPill(stats_row, "Downloaded", "—")
        self._downloaded_pill.pack(side="left", padx=(0, theme.SPACE_6))
        self._size_pill = StatPill(stats_row, "Disk used", "—")
        self._size_pill.pack(side="left")

        self._refresh_btn = IconButton(
            header, "Refresh", icon="refresh", command=self._refresh
        )
        self._refresh_btn.pack(side="right")
        self._download_all_btn = IconButton(
            header,
            "Download all",
            icon="download",
            variant="primary",
            command=self._download_all,
        )
        self._download_all_btn.pack(side="right", padx=(0, theme.SPACE_2))

    def _build_scroll(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"])
        self._scroll.pack(
            fill="both", expand=True, padx=theme.PAGE_GUTTER, pady=(0, theme.SPACE_5)
        )
        bind_mousewheel(self._scroll)
        self._loading_overlay = LoadingOverlay(self._scroll, "Scanning…")

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        if self._loading:
            return
        self._loading = True
        self._refresh_btn.configure(state="disabled")
        for child in self._scroll.winfo_children():
            child.destroy()
        self._rows = {}
        self._loading_overlay.show()
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        report = build_resource_report(self.shell.models)
        self._schedule(self._on_scan_complete, report)

    def _on_scan_complete(self, report: ResourceReport) -> None:
        if not self.winfo_exists():
            return
        self._loading = False
        self._loading_overlay.hide()
        self._refresh_btn.configure(state="normal")
        self._report = report
        self._render(report)

    def _render(self, report: ResourceReport) -> None:
        cached = sum(1 for t in report.tokenizers if t.is_cached)
        self._downloaded_pill.set_text(f"{cached} of {len(report.tokenizers)}")
        self._size_pill.set_text(formatting.fmt_bytes(report.total_tokenizer_bytes))

        section_label(self._scroll, "Tokenizers").pack(
            fill="x", pady=(0, theme.SPACE_2)
        )
        for resource in report.tokenizers:
            row = _TokenizerRow(
                self._scroll,
                resource,
                is_downloading=self.is_downloading,
                is_busy=self.is_busy,
                start_download=self.start_download,
                cancel_download=self.cancel_download,
            )
            row.pack(fill="x", pady=theme.SPACE_1)
            self._rows[resource.key] = row

        section_label(self._scroll, "Storage").pack(
            fill="x", pady=(theme.SPACE_4, theme.SPACE_2)
        )
        for managed_dir in report.dirs:
            _DirRow(self._scroll, managed_dir).pack(fill="x", pady=theme.SPACE_1)

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------

    def is_busy(self) -> bool:
        return self._downloading_key is not None

    def is_downloading(self, key: str) -> bool:
        return self._downloading_key == key

    def start_download(self, resource: TokenizerResource) -> None:
        if self.is_busy():
            return
        self._downloading_key = resource.key
        self._cancel_event = threading.Event()
        for row in self._rows.values():
            row.refresh_action()
        threading.Thread(
            target=self._download_worker,
            args=(resource, self._cancel_event),
            daemon=True,
        ).start()

    def cancel_download(self) -> None:
        self._download_queue = []
        if self._cancel_event is not None:
            self._cancel_event.set()

    def _download_all(self) -> None:
        if self.is_busy() or self._report is None:
            return
        missing = [t for t in self._report.tokenizers if not t.is_cached]
        if not missing:
            return
        self._download_queue = [t.key for t in missing[1:]]
        self.start_download(missing[0])

    def _advance_queue(self) -> None:
        if not self._download_queue or self._report is None:
            return
        next_key = self._download_queue.pop(0)
        resource = next(
            (t for t in self._report.tokenizers if t.key == next_key), None
        )
        if resource is not None and not resource.is_cached:
            self.start_download(resource)

    def _download_worker(
        self, resource: TokenizerResource, cancel_event: threading.Event
    ) -> None:
        def on_progress(downloaded: int, total: int | None) -> None:
            self._schedule(self._on_download_progress, resource.key, downloaded, total)

        try:
            updated = download_tokenizer(
                resource, on_progress=on_progress, cancel_event=cancel_event
            )
            self._schedule(self._on_download_complete, updated)
        except ResourceDownloadError as exc:
            self._schedule(self._on_download_failed, resource, str(exc))
        except Exception:
            self._schedule(self._on_download_cancelled, resource)

    def _on_download_progress(
        self, key: str, downloaded: int, total: int | None
    ) -> None:
        row = self._rows.get(key)
        if row is not None:
            row.set_progress(downloaded, total)

    def _on_download_complete(self, resource: TokenizerResource) -> None:
        self._downloading_key = None
        self._cancel_event = None
        row = self._rows.get(resource.key)
        if row is not None:
            row.set_resource(resource)
        if self._report is not None:
            self._report = ResourceReport(
                tokenizers=[
                    resource if t.key == resource.key else t
                    for t in self._report.tokenizers
                ],
                dirs=self._report.dirs,
                total_tokenizer_bytes=self._report.total_tokenizer_bytes
                + (resource.size_bytes or 0),
            )
            cached = sum(1 for t in self._report.tokenizers if t.is_cached)
            total = len(self._report.tokenizers)
            self._downloaded_pill.set_text(f"{cached} of {total}")
            self._size_pill.set_text(
                formatting.fmt_bytes(self._report.total_tokenizer_bytes)
            )
        for r in self._rows.values():
            r.refresh_action()
        self._advance_queue()

    def _on_download_failed(self, resource: TokenizerResource, message: str) -> None:
        self._downloading_key = None
        self._cancel_event = None
        failed = TokenizerResource(
            key=resource.key,
            backend=resource.backend,
            name=resource.name,
            model_ids=resource.model_ids,
            is_cached=False,
            cache_path=None,
            size_bytes=None,
            source_url=resource.source_url,
            notes=message,
        )
        row = self._rows.get(resource.key)
        if row is not None:
            row.set_resource(failed)
        for r in self._rows.values():
            r.refresh_action()
        self._advance_queue()

    def _on_download_cancelled(self, resource: TokenizerResource) -> None:
        self._downloading_key = None
        self._cancel_event = None
        for r in self._rows.values():
            r.refresh_action()
        self._advance_queue()
