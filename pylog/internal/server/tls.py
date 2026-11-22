"""Chapter 5 — TLS helpers (grpcio credentials from PEM files).

The book's flow: a CA (``ca.pem`` / ``ca-key.pem``) signs a server
certificate (``server.pem`` / ``server-key.pem``) and client
certificates (``root-client.pem`` / ``nobody-client.pem`` ...). The
server presents its cert and trusts the CA to verify clients (mTLS);
the client trusts the CA to verify the server and presents its own
cert. ``scripts/make_certs.sh`` generates these files; the helpers
below only load them.
"""

import grpc


def _read(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def server_credentials(ca_cert: str, server_cert: str, server_key: str):
    """mTLS server credentials: present the server cert, require and
    verify client certs against the CA."""
    return grpc.ssl_server_credentials(
        [( _read(server_key), _read(server_cert))],
        root_certificates=_read(ca_cert),
        require_client_auth=True,
    )


def client_credentials(ca_cert: str, client_cert: str, client_key: str):
    """mTLS client credentials: verify the server against the CA,
    present the client cert."""
    return grpc.ssl_channel_credentials(
        root_certificates=_read(ca_cert),
        private_key=_read(client_key),
        certificate_chain=_read(client_cert),
    )
