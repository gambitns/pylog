from pylog.internal.server.http import new_http_server

if __name__ == "__main__":
    srv = new_http_server(":8080")
    print("Serving on :8080")
    srv.serve_forever()
