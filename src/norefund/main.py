"""Entry point: launch GUI or run CLI."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="norefund",
        description="NoRefund — Know your token count and cost before you run.",
    )
    parser.add_argument("--gui", action="store_true", help="Launch the desktop GUI")
    parser.add_argument("file", nargs="?", help="Path to file to analyze")
    parser.add_argument("--model", default="openai:gpt-4o", help="Model ID to use")

    args = parser.parse_args()

    if args.gui or args.file is None:
        _run_gui()
    else:
        _run_cli(args.file, args.model)


def _run_gui() -> None:
    from norefund.gui.app import App
    app = App()
    app.mainloop()


def _run_cli(file_path: str, model_id: str) -> None:
    from norefund.core.service import analyze_file
    from pathlib import Path

    result = analyze_file(Path(file_path), model_id)
    print(f"File      : {result.file_path}")
    print(f"Tokens    : {result.token_count:,}")
    print(f"Context   : {result.context_usage_pct:.1f}% of {result.context_window:,}")
    print(f"Fits      : {'Yes' if result.fits_in_context else 'No — needs chunking'}")
    print(f"Min chunks: {result.min_chunks_needed}")
    print(f"Est. cost : ${result.estimated_input_cost:.6f} USD (input only)")


if __name__ == "__main__":
    main()
