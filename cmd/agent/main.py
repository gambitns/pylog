"""Chapter 10 — the agent command-line interface.

The book's agent CLI (``cmd/server/main.go`` in Part 4) is the Docker
image's entry point: parse flags, configure the agent, run it. Flags
mirror the book's: node id, data directory, RPC address, the address
to bind, and the addresses of nodes to join.

Usage:
  python -m cmd.agent.main --node-id node-1 --data-dir /tmp/pylog-1 \\
      --rpc-addr 127.0.0.1:8401 --join 127.0.0.1:8402
"""

import argparse
import time

from pylog.internal.agent.agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser(description="pylog agent")
    parser.add_argument("--node-id", default="node-1")
    parser.add_argument("--data-dir", default="/tmp/pylog-data")
    parser.add_argument("--rpc-addr", default="127.0.0.1:8401")
    parser.add_argument("--join", action="append", default=[],
                        help="peer RPC address to join (repeatable)")
    args = parser.parse_args()

    agent = Agent(args.node_id, args.data_dir, args.rpc_addr,
                  peers=args.join)
    agent.start()
    print(f"pylog agent {args.node_id} serving on {args.rpc_addr}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        agent.shutdown()


if __name__ == "__main__":
    main()
