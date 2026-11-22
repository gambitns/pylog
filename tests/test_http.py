"""Day 2 — JSON/HTTP server (chat Day 2). Tests the handler functions
directly and the live server over real HTTP, including the book's curl
examples: produce three records, consume them back, 404 on offset 99.
"""
import base64
import json
import threading
import unittest
import urllib.request
import urllib.error

from pylog.internal.server.http import _handle_consume, _handle_produce, _HTTPServer, new_http_server


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode("ascii")


class TestHandlers(unittest.TestCase):
    def test_produce_consume_round_trip(self):
        srv = _HTTPServer()
        status, payload = _handle_produce(srv, {"record": {"value": _b64("Let's Go #1")}})
        self.assertEqual((status, payload), (200, {"offset": 0}))
        status, payload = _handle_consume(srv, {"offset": 0})
        self.assertEqual(status, 200)
        self.assertEqual(payload["record"]["value"], _b64("Let's Go #1"))
        self.assertEqual(payload["record"]["offset"], 0)

    def test_bad_produce_is_400(self):
        srv = _HTTPServer()
        status, _ = _handle_produce(srv, {"record": {"value": "!!!not-base64!!!"}})
        self.assertEqual(status, 400)

    def test_missing_offset_is_404(self):
        srv = _HTTPServer()
        status, payload = _handle_consume(srv, {"offset": 99})
        self.assertEqual((status, payload), (404, {"error": "offset not found"}))


class TestLiveServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = new_http_server(":18080")
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _curl(self, method, data):
        req = urllib.request.Request(
            "http://127.0.0.1:18080/", method=method,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_book_curl_examples(self):
        for i, name in enumerate(["Let's Go #1", "Let's Go #2", "Let's Go #3"]):
            status, payload = self._curl("POST", {"record": {"value": _b64(name)}})
            self.assertEqual((status, payload), (200, {"offset": i}))
        status, payload = self._curl("GET", {"offset": 1})
        self.assertEqual(status, 200)
        self.assertEqual(payload["record"]["value"], _b64("Let's Go #2"))


if __name__ == "__main__":
    unittest.main()
