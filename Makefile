project := jaeger_client_contrib
projects := jaeger_client_contrib
flake8 := flake8
COV_DIRS := $(projects:%=--cov %)
pytest_args := -s --tb short --cov-config .coveragerc $(COV_DIRS) tests
pytest := py.test $(pytest_args)
test_args := --cov-report term-missing --cov-report xml --junitxml junit.xml
cover_args := --cov-report html


.PHONY: bootstrap
bootstrap:
	[ "$$VIRTUAL_ENV" != "" ]
	rm -rf *.egg-info || true
	pip install -U 'pip>=7.0,<8.0'
	pip install -e '.'
	pip install -e '.[tests]'
	python setup.py develop

.PHONY: test
test: clean
	$(pytest) $(test_args)

.PHONY: test_ci
test_ci: clean test lint

.PHONY: cover
cover: clean
	$(pytest) $(cover_args) --benchmark-skip
	open htmlcov/index.html

.PHONY: clean
clean:
	@find $(project) "(" -name "*.pyc" -o -name "coverage.xml" -o -name "junit.xml" ")" -delete
	@find tests "(" -name "*.pyc" -o -name "coverage.xml" -o -name "junit.xml" -o -name __pycache__ ")" -delete
	@find . "(" -name "*.pyc" -o -name "coverage.xml" -o -name "junit.xml" -o -name __pycache__ ")" -delete
	@rm -rf jaeger_client_contrib.egg-info
	@rm -f .coverage

.PHONY: lint
lint:
	$(flake8) $(projects) tests
