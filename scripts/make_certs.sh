#!/bin/sh
# Chapter 5 — generate the test CA and certificates.
# The book is its own CA with CFSSL; this script runs exactly that
# flow when cfssl/cfssljson are installed, and falls back to openssl
# otherwise. Output goes to testdata/certs/. These are TEST
# certificates only — never ship the test CA's private key.
set -e
cd "$(dirname "$0")/../testdata/certs"

if command -v cfssl >/dev/null 2>&1; then
  echo "Using cfssl (book's flow)"
  cfssl gencert -initca ca-csr.json | cfssljson -bare ca
  cfssl gencert -ca=ca.pem -ca-key=ca-key.pem \
    -config=ca-config.json -profile=server server-csr.json \
    | cfssljson -bare server
  cfssl gencert -ca=ca.pem -ca-key=ca-key.pem \
    -config=ca-config.json -profile=client client-csr.json \
    | cfssljson -bare root-client
  cfssl gencert -ca=ca.pem -ca-key=ca-key.pem \
    -config=ca-config.json -profile=client nobody-csr.json \
    | cfssljson -bare nobody-client
else
  echo "cfssl not found — falling back to openssl (same shapes, same names)"
  openssl req -x509 -newkey rsa:2048 -keyout ca-key.pem -out ca.pem \
    -days 365 -nodes -subj "/CN=pylog-test-ca"
  openssl req -newkey rsa:2048 -keyout server-key.pem -out server.csr \
    -nodes -subj "/CN=localhost"
  openssl x509 -req -in server.csr -CA ca.pem -CAkey ca-key.pem \
    -CAcreateserial -out server.pem -days 365
  openssl req -newkey rsa:2048 -keyout root-client-key.pem \
    -out root-client.csr -nodes -subj "/CN=root"
  openssl x509 -req -in root-client.csr -CA ca.pem -CAkey ca-key.pem \
    -CAcreateserial -out root-client.pem -days 365
  openssl req -newkey rsa:2048 -keyout nobody-client-key.pem \
    -out nobody-client.csr -nodes -subj "/CN=nobody"
  openssl x509 -req -in nobody-client.csr -CA ca.pem -CAkey ca-key.pem \
    -CAcreateserial -out nobody-client.pem -days 365
  rm -f *.csr *.srl
fi
echo "Certificates written to testdata/certs/"
ls -1 *.pem
