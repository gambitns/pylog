"""Chapter 5 — securing the service, in the book's three steps.

1. Encrypt in-flight data: TLS authenticates the *server* (the client
   checks the server's certificate against the CA).
2. Authenticate clients: mutual TLS — the server also checks the
   client's certificate, so it knows *who* is calling.
3. Authorize: an access control list decides what that client may do.
   The book uses Casbin with a model + policy file; here the policy
   starts as a readable function (``authorize``) over a plain dict, and
   Casbin's Python port is the drop-in upgrade — see ``POLICY`` below.

Certificates: the book is its own CA with CFSSL (``cfssl`` /
``cfssljson``, configs in ``testdata/certs/``). ``scripts/make_certs.sh``
runs exactly that flow when cfssl is installed, and falls back to
``openssl`` otherwise. The generated files are test-only; never ship
the test CA's private key.

How identity reaches the authorizer: with mTLS, grpcio exposes the
peer's certificate; ``subject_from_context`` reads the Common Name
from it. The book's ACL maps subjects to permissions:
``root`` may do everything; ``nobody`` may do nothing.
"""

import grpc

# The book's policy, as data. subject -> set of allowed RPCs.
# "root" is the super-user in the book's tests; "nobody" is the
# unauthenticated / unprivileged subject used to prove denial works.
POLICY: dict[str, set[str]] = {
    "root": {"Produce", "Consume", "ConsumeStream", "ProduceStream", "GetServers"},
    "nobody": set(),
}


def authorize(subject: str, method: str, policy: dict | None = None) -> bool:
    """True if ``subject`` may call the RPC named ``method``.
    Unknown subjects are denied — fail closed, as in the book."""
    allowed = (policy or POLICY).get(subject, set())
    return method in allowed


def subject_from_context(context) -> str:
    """Common Name of the peer certificate, or ``"nobody"`` when there
    is none / it cannot be parsed. grpcio exposes the peer cert chain
    via ``context.auth_context()`` under the ``x509_common_name`` key."""
    try:
        auth = context.auth_context()
        names = auth.get("x509_common_name", [])
        if names:
            return names[0].decode() if isinstance(names[0], bytes) else names[0]
    except Exception:
        pass
    return "nobody"


class AuthInterceptor(grpc.ServerInterceptor):
    """Unary + streaming interceptor: authenticate (mTLS identity),
    then authorize (ACL). Denied calls get PERMISSION_DENIED, the
    gRPC equivalent of the book's Casbin enforcer returning false."""

    def __init__(self, policy: dict | None = None) -> None:
        self.policy = policy or POLICY

    def _check(self, context, method: str) -> bool:
        rpc_name = method.rsplit("/", 1)[-1]
        return authorize(subject_from_context(context), rpc_name, self.policy)

    def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method
        handler = continuation(handler_call_details)
        if handler is None:
            return None

        def _deny(context):
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "permission denied")

        if handler.unary_unary is not None:
            orig = handler.unary_unary

            def unary_unary(request, context):
                if not self._check(context, method):
                    _deny(context)
                return orig(request, context)

            return handler._replace(unary_unary=unary_unary)
        if handler.unary_stream is not None:
            orig = handler.unary_stream

            def unary_stream(request, context):
                if not self._check(context, method):
                    _deny(context)
                yield from orig(request, context)

            return handler._replace(unary_stream=unary_stream)
        if handler.stream_unary is not None:
            orig = handler.stream_unary

            def stream_unary(request_iterator, context):
                if not self._check(context, method):
                    _deny(context)
                return orig(request_iterator, context)

            return handler._replace(stream_unary=stream_unary)
        if handler.stream_stream is not None:
            orig = handler.stream_stream

            def stream_stream(request_iterator, context):
                if not self._check(context, method):
                    _deny(context)
                yield from orig(request_iterator, context)

            return handler._replace(stream_stream=stream_stream)
        return handler
