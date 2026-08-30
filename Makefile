.PHONY: install run test e2e screenshots docs-check docker

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r requirements-dev.txt
	npm ci

run:
	.venv/bin/python app.py

test:
	.venv/bin/pytest -q

e2e:
	PYTHON_EXECUTABLE=.venv/bin/python npm run test:e2e

screenshots:
	PYTHON_EXECUTABLE=.venv/bin/python npm run screenshots

docs-check:
	.venv/bin/python scripts/check_docs.py

docker:
	docker build -t speaktrain:v0.6.0 .
