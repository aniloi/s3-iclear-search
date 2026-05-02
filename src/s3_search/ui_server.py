"""Entry point for the s3-search-ui command — starts the FastAPI server."""

from __future__ import annotations

import argparse
import sys
import threading
import time
import webbrowser


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="s3-search-ui",
        description="Launch the S3 Fintrans Search web UI.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to run the server on (default: 8080).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0).",
    )
    return parser


def _open_browser(port: int, delay: float = 1.5) -> None:
    """Open the default browser after a short delay to let the server start."""
    time.sleep(delay)
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    """Main entry point for s3-search-ui."""
    parser = _build_parser()
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print(
            "Error: uvicorn is not installed. "
            "Install the UI dependencies: pip install 's3-fintrans-search[ui]'",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"S3 Search UI running at http://localhost:{args.port}")
    print("Press Ctrl+C to stop the server.")

    if not args.no_browser:
        browser_thread = threading.Thread(
            target=_open_browser,
            args=(args.port,),
            daemon=True,
        )
        browser_thread.start()

    uvicorn.run(
        "s3_search.api.app:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
