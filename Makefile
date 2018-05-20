lint:
	isort -rc .
test:
	flake8
	./scripts/permissions_checker.py
	mypy pulsar/
	pytest --cov-report term-missing --cov-branch --cov=pulsar tests/
tests: test
