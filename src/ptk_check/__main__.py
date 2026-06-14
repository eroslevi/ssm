"""
CLI entry point.

  python -m ptk_check ingest --file ptk.txt
  python -m ptk_check serve [--host 0.0.0.0] [--port 8000]
"""
from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _cmd_ingest(args: argparse.Namespace) -> None:
    from .parser  import parse_ptk
    from .indexer import build_index

    ptk_path = Path(args.file)
    if not ptk_path.exists():
        print(f"Error: file not found: {ptk_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing {ptk_path} ...")
    t0       = time.time()
    articles = parse_ptk(str(ptk_path))
    print(f"  parsed {len(articles)} articles in {time.time() - t0:.1f}s")

    print("Building indexes ...")
    t0 = time.time()
    build_index(articles, data_dir=args.data_dir)
    print(f"  done in {time.time() - t0:.1f}s")


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn
    url = f"http://{args.host}:{args.port}"
    print(f"Starting server → {url}")

    def _run_server() -> None:
        uvicorn.run(
            "ptk_check.web.server:app",
            host=args.host,
            port=args.port,
            reload=False,
        )

    t = threading.Thread(target=_run_server, daemon=True)
    t.start()

    if _wait_for_port(args.host, args.port):
        webbrowser.open(url)
    else:
        print(f"Server did not start in time — open {url} manually", file=sys.stderr)

    t.join()


def main() -> None:
    parser = argparse.ArgumentParser(prog="ptk_check")
    sub    = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Parse PTK file and build indexes")
    p_ingest.add_argument("--file",     required=True, help="Path to ptk.txt")
    p_ingest.add_argument("--data-dir", default="data", help="Output directory (default: data)")

    p_serve = sub.add_parser("serve", help="Start web UI")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", default=8000, type=int)

    args = parser.parse_args()
    if args.command == "ingest":
        _cmd_ingest(args)
    elif args.command == "serve":
        _cmd_serve(args)


if __name__ == "__main__":
    main()
