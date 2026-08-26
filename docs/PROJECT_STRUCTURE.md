# Project Structure

A map of every directory in the repo, so you can find the right file without opening
each one to check. For *why* the code is split this way, see
[Architecture](ARCHITECTURE.md).

## File tree

```
NoRefund/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   ├── DATA_SOURCES.md
│   ├── MATHEMATICS.md
│   └── PROJECT_STRUCTURE.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── app/
│   │   │   │   ├── hardware-logos/
│   │   │   │   │   ├── LICENSE
│   │   │   │   │   └── index.tsx
│   │   │   │   ├── provider-logos/
│   │   │   │   │   ├── LICENSE
│   │   │   │   │   └── index.tsx
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── ContextBar.tsx
│   │   │   │   ├── EmptyState.tsx
│   │   │   │   ├── HardwareBadge.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── ModelSelect.tsx
│   │   │   │   ├── NoticeBanner.tsx
│   │   │   │   ├── ProcessingDialog.tsx
│   │   │   │   ├── ProviderBadge.tsx
│   │   │   │   ├── SectionLabel.tsx
│   │   │   │   ├── Select.tsx
│   │   │   │   ├── SettingsModal.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Spinner.tsx
│   │   │   │   ├── StatPill.tsx
│   │   │   │   └── TabBar.tsx
│   │   │   └── ui/
│   │   │       ├── alert.tsx
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── checkbox.tsx
│   │   │       ├── dialog.tsx
│   │   │       ├── input.tsx
│   │   │       ├── label.tsx
│   │   │       ├── progress.tsx
│   │   │       ├── select.tsx
│   │   │       ├── skeleton.tsx
│   │   │       ├── switch.tsx
│   │   │       ├── table.tsx
│   │   │       ├── tabs.tsx
│   │   │       ├── textarea.tsx
│   │   │       ├── tooltip.tsx
│   │   │       └── utils.ts
│   │   ├── hooks/
│   │   │   ├── useBridge.ts
│   │   │   ├── useDelayedFlag.ts
│   │   │   ├── useFileDrop.ts
│   │   │   ├── useJob.ts
│   │   │   ├── useReducedMotion.ts
│   │   │   ├── useSettings.ts
│   │   │   ├── useShortcuts.ts
│   │   │   └── useTheme.ts
│   │   ├── lib/
│   │   │   ├── appContext.ts
│   │   │   ├── bridge.test.ts
│   │   │   ├── bridge.ts
│   │   │   ├── cn.ts
│   │   │   ├── costing.test.ts
│   │   │   ├── costing.ts
│   │   │   ├── format.test.ts
│   │   │   ├── format.ts
│   │   │   ├── parsing.test.ts
│   │   │   ├── parsing.ts
│   │   │   ├── types.ts
│   │   │   ├── views.test.ts
│   │   │   └── views.ts
│   │   ├── styles/
│   │   │   ├── card-art.css
│   │   │   ├── contrast.test.ts
│   │   │   ├── index.css
│   │   │   ├── motion.css
│   │   │   ├── scrollbars.css
│   │   │   ├── theme.css
│   │   │   └── typography.css
│   │   ├── views/
│   │   │   ├── Calculator/
│   │   │   │   ├── ContextCard.tsx
│   │   │   │   ├── CostCard.tsx
│   │   │   │   ├── ModelPicker.tsx
│   │   │   │   ├── TokenInputs.tsx
│   │   │   │   └── index.tsx
│   │   │   ├── Compare/
│   │   │   │   ├── InputCard.tsx
│   │   │   │   ├── ModelChecklist.tsx
│   │   │   │   ├── ProjectionRow.tsx
│   │   │   │   ├── ProjectionTab.tsx
│   │   │   │   ├── ResultRow.tsx
│   │   │   │   ├── index.tsx
│   │   │   │   ├── sort.test.ts
│   │   │   │   └── sort.ts
│   │   │   ├── FitCheck/
│   │   │   │   ├── BreakdownCard.tsx
│   │   │   │   ├── ConfigCard.tsx
│   │   │   │   ├── UtilizationCard.tsx
│   │   │   │   ├── VerdictHeader.tsx
│   │   │   │   ├── Warnings.tsx
│   │   │   │   └── index.tsx
│   │   │   ├── Parser/
│   │   │   │   ├── AnalysisProgress.tsx
│   │   │   │   ├── FileStrip.tsx
│   │   │   │   ├── LogsPanel.tsx
│   │   │   │   ├── ResultsTable.tsx
│   │   │   │   ├── StatusBar.tsx
│   │   │   │   ├── Toolbar.tsx
│   │   │   │   └── index.tsx
│   │   │   ├── Registry/
│   │   │   │   ├── ModelCard.tsx
│   │   │   │   ├── ProviderFilter.tsx
│   │   │   │   └── index.tsx
│   │   │   ├── Resources/
│   │   │   │   ├── StorageRow.tsx
│   │   │   │   ├── TokenizerRow.tsx
│   │   │   │   └── index.tsx
│   │   │   ├── DebugBridge.tsx
│   │   │   └── Gallery.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── README.md
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── packaging/
│   ├── windows/
│   │   ├── build.ps1
│   │   └── installer.iss
│   ├── README.md
│   ├── build.py
│   ├── macos_setup.py
│   └── norefund.spec
├── src/
│   └── norefund/
│       ├── assets/
│       │   └── icons/
│       │       ├── providers/
│       │       │   ├── LICENSE
│       │       │   ├── anthropic.png
│       │       │   ├── deepseek.png
│       │       │   ├── google.png
│       │       │   ├── meta.png
│       │       │   ├── mistral.png
│       │       │   └── openai.png
│       │       ├── LICENSE
│       │       ├── bar_chart.png
│       │       ├── calculator.png
│       │       ├── check.png
│       │       ├── check_circle.png
│       │       ├── chevron_down.png
│       │       ├── download.png
│       │       ├── external_link.png
│       │       ├── file_text.png
│       │       ├── folder_open.png
│       │       ├── folder_plus.png
│       │       ├── hard_drive.png
│       │       ├── hash.png
│       │       ├── layers.png
│       │       ├── moon.png
│       │       ├── plus.png
│       │       ├── refresh.png
│       │       ├── settings.png
│       │       ├── sun.png
│       │       ├── warning.png
│       │       ├── x.png
│       │       ├── x_circle.png
│       │       └── zap.png
│       ├── config/
│       │   ├── default_models.yaml
│       │   ├── hardware.yaml
│       │   └── model_architectures.yaml
│       ├── core/
│       │   ├── report/
│       │   │   ├── __init__.py
│       │   │   ├── _format.py
│       │   │   ├── html.py
│       │   │   ├── model.py
│       │   │   └── pdf.py
│       │   ├── resources/
│       │   │   ├── __init__.py
│       │   │   ├── download.py
│       │   │   ├── probe.py
│       │   │   ├── report.py
│       │   │   └── types.py
│       │   ├── __init__.py
│       │   ├── architectures.py
│       │   ├── compare.py
│       │   ├── costing.py
│       │   ├── currency.py
│       │   ├── export.py
│       │   ├── hardware_registry.py
│       │   ├── models_registry.py
│       │   ├── parsing.py
│       │   ├── paths.py
│       │   ├── portfolio.py
│       │   ├── quantization.py
│       │   ├── secrets.py
│       │   ├── selfhost.py
│       │   ├── service.py
│       │   ├── settings.py
│       │   └── tokenization.py
│       ├── desktop/
│       │   ├── __init__.py
│       │   ├── api.py
│       │   ├── app.py
│       │   ├── dto.py
│       │   └── jobs.py
│       ├── __init__.py
│       ├── logging_config.py
│       └── main.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_architectures.py
│   ├── test_compare.py
│   ├── test_costing.py
│   ├── test_currency.py
│   ├── test_desktop_api.py
│   ├── test_desktop_app.py
│   ├── test_desktop_dto.py
│   ├── test_desktop_jobs.py
│   ├── test_export.py
│   ├── test_hardware_registry.py
│   ├── test_models_registry.py
│   ├── test_parsing.py
│   ├── test_paths.py
│   ├── test_portfolio.py
│   ├── test_quantization.py
│   ├── test_registry_data.py
│   ├── test_report.py
│   ├── test_resources.py
│   ├── test_secrets.py
│   ├── test_selfhost.py
│   ├── test_service.py
│   ├── test_settings.py
│   └── test_tokenization.py
├── LICENSE
├── README.md
├── pyproject.toml
└── uv.lock
```

## Top level

| Path | What's there |
|---|---|
| [`src/norefund/`](../src/norefund/) | The Python package: CLI, desktop shell, and all core logic |
| [`frontend/`](../frontend/) | The React UI |
| [`tests/`](../tests/) | Python test suite (pytest) |
| [`packaging/`](../packaging/) | Build scripts and installer configs for Windows/macOS/Linux |
| [`config/`](../src/norefund/config/) | Model/hardware registry YAML — see [Data Sources](DATA_SOURCES.md) |
| [`.github/workflows/`](../.github/workflows/) | CI (lint + test) and release (cross-platform build + GitHub Release) pipelines |
| [`docs/`](.) | This documentation |

## `src/norefund/`

| Path | What's there |
|---|---|
| [`main.py`](../src/norefund/main.py) | Entry point: launches the CLI analyze mode or the desktop GUI |
| [`__init__.py`](../src/norefund/__init__.py) | Package version (`__version__`) — single source of truth for the app version |
| [`logging_config.py`](../src/norefund/logging_config.py) | Application-wide structured JSON logging |
| [`core/`](../src/norefund/core/) | Pure logic — parsing, tokenizing, costing, self-host math. No UI imports. See [Architecture](ARCHITECTURE.md#core--pure-logic) |
| [`core/report/`](../src/norefund/core/report/) | PDF/HTML report rendering from one shared `ReportModel` |
| [`core/resources/`](../src/norefund/core/resources/) | Tokenizer cache inventory and downloads |
| [`desktop/`](../src/norefund/desktop/) | pywebview shell and JS bridge — marshals arguments only, no business logic. See [Architecture](ARCHITECTURE.md#desktop--the-pywebview-shell-and-js-bridge) |
| [`config/`](../src/norefund/config/) | `default_models.yaml`, `model_architectures.yaml`, `hardware.yaml` — the registry data itself |

## `frontend/src/`

| Path | What's there |
|---|---|
| [`App.tsx`](../frontend/src/App.tsx) | Root component: theme, view routing, top-level layout |
| [`main.tsx`](../frontend/src/main.tsx) | React entry point |
| [`lib/`](../frontend/src/lib/) | Bridge client, TypeScript type mirrors, formatting helpers — see [Architecture](ARCHITECTURE.md#frontend--the-react-ui) |
| [`hooks/`](../frontend/src/hooks/) | `useJob`, `useBridge`, `useSettings`, `useTheme`, `useFileDrop`, … |
| [`views/`](../frontend/src/views/) | One folder per feature: `Calculator/`, `Parser/`, `Compare/`, `FitCheck/`, `Registry/`, `Resources/` |
| [`components/app/`](../frontend/src/components/app/) | App-specific composite components (`Sidebar`, `Header`, `ModelSelect`, `ProcessingDialog`, …) |
| [`components/ui/`](../frontend/src/components/ui/) | Low-level UI primitives (`button`, `dialog`, `table`, `tabs`, …) |
| [`styles/`](../frontend/src/styles/) | Global CSS: theme tokens, motion tokens, typography, scrollbars |

## `tests/`

Mirrors `src/norefund/` module-for-module (`test_costing.py` tests `core/costing.py`,
etc.), plus [`conftest.py`](../tests/conftest.py) for shared fixtures. Every `core/`
module with logic worth verifying has a matching test file — see
[Contributing](CONTRIBUTING.md#tests) for what's expected of a new one.

## `packaging/`

| Path | What's there |
|---|---|
| [`build.py`](../packaging/build.py) | Cross-platform build orchestration (frontend build → PyInstaller/py2app) |
| [`norefund.spec`](../packaging/norefund.spec) | PyInstaller spec for Windows/Linux |
| [`macos_setup.py`](../packaging/macos_setup.py) | py2app setup script for the macOS `.app` bundle |
| [`windows/installer.iss`](../packaging/windows/installer.iss) | Inno Setup script for the Windows installer |
| [`windows/build.ps1`](../packaging/windows/build.ps1) | Windows build helper script |
| [`README.md`](../packaging/README.md) | Build/run commands per platform, packaging-safety notes |

## `.github/workflows/`

| File | Runs on | Does |
|---|---|---|
| [`ci.yml`](../.github/workflows/ci.yml) | Every PR and push to `main` | `pytest` + `ruff check` |
| [`build.yml`](../.github/workflows/build.yml) | Every PR and push to `main` | Cross-platform frozen-build smoke test |
| [`release.yml`](../.github/workflows/release.yml) | A pushed version tag | Builds signed artifacts for Windows/macOS/Linux and publishes a GitHub Release |
