compile:
	python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. pylog/api/v1/log.proto

test:
	python3 -m unittest discover -s tests -v

test-fast:
	python3 -m unittest discover -s tests

certs:
	sh scripts/make_certs.sh

run-http:
	python3 -m cmd.server.main

run-grpc:
	python3 -m cmd.grpc_server.main

run-agent:
	python3 -m cmd.agent.main

docker:
	docker build -f deploy/Dockerfile -t pylog:latest .

kind:
	kind create cluster --config deploy/kind/cluster.yaml

helm-install:
	helm install pylog deploy/helm/pylog

.PHONY: compile test test-fast certs run-http run-grpc run-agent docker kind helm-install
