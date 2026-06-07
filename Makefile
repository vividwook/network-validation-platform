.PHONY: validate-sot generate deploy-lab collect-state validate report test test-integration destroy-lab

validate-sot:
	PYTHONPATH=src python -m nvp.cli validate-sot

generate:
	PYTHONPATH=src python -m nvp.cli generate

deploy-lab:
	containerlab deploy -t containerlab/evpn.yml

collect-state:
	PYTHONPATH=src python -m nvp.cli collect-state

validate:
	PYTHONPATH=src python -m nvp.cli validate

report:
	PYTHONPATH=src python -m nvp.cli report

test:
	pytest

test-integration:
	NVP_RUN_LIVE_TESTS=1 pytest -m integration

destroy-lab:
	containerlab destroy -t containerlab/evpn.yml
