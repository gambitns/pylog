"""Chapter 7 — driving the real Serf agent from Python.

The book embeds Serf as a Go library; there is no equivalent Python
library, so the full build runs Serf as a subprocess and talks to it
over its RPC / HTTP interface. This module is the bridge: it starts
``serf agent``, joins a cluster, and reports membership events.

Requires the ``serf`` binary on PATH (``go install`` it, or download a
release from hashicorp.com). If it is not installed, ``SerfAgent``
raises a clear error at construction time — it never pretends the
in-process ``Membership`` gossip *is* Serf.
"""

import json
import shutil
import subprocess
import urllib.request


class SerfNotInstalledError(RuntimeError):
    pass


class SerfAgent:
    def __init__(self, node_name: str, bind_addr: str = "127.0.0.1:7946",
                 rpc_addr: str = "127.0.0.1:7373") -> None:
        if shutil.which("serf") is None:
            raise SerfNotInstalledError(
                "serf binary not found on PATH; install it from "
                "https://www.serf.io/downloads or use "
                "pylog.internal.discovery.Membership instead"
            )
        self.node_name = node_name
        self.bind_addr = bind_addr
        self.rpc_addr = rpc_addr
        self._proc: subprocess.Popen | None = None

    def start(self, join_addrs: list[str] | None = None) -> None:
        cmd = [
            "serf", "agent",
            "-node", self.node_name,
            "-bind", self.bind_addr,
            "-rpc-addr", self.rpc_addr,
        ]
        for addr in join_addrs or []:
            cmd += ["-join", addr]
        self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True)

    def members(self) -> list[dict]:
        """Member list via Serf's HTTP API (``/v1/agent/members``)."""
        with urllib.request.urlopen(
            f"http://{self.rpc_addr}/v1/agent/members", timeout=5
        ) as resp:
            return json.load(resp)

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait(timeout=5)
            self._proc = None
