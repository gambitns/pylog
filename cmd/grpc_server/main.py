"""Chapter 4 — run the gRPC server (single node, no Raft).

Usage: ``python -m cmd.grpc_server.main [--addr [::]:8400] [--data-dir /tmp/pylog]``
"""

import argparse
import time

from pylog.internal.log import Log as DurableLog
from pylog.internal.server.grpc_server import new_grpc_server


def main() -> None:
    parser = argparse.ArgumentParser(description="pylog gRPC server")
    parser.add_argument("--addr", default="[::]:8400")
    parser.add_argument("--data-dir", default="/tmp/pylog-data")
    args = parser.parse_args()

    log = DurableLog(args.data_dir)
    server = new_grpc_server(log, addr=args.addr)
    server.start()
    print(f"pylog gRPC serving on {args.addr} (data: {args.data_dir})")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop(grace=2)
        log.close()


if __name__ == "__main__":
    main()
