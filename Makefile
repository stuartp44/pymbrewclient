# Variables
PYTHON = python
PIP = $(PYTHON) -m pip
COVERAGE = coverage
PYTEST = pytest
REQ_FILE = requirements.txt
SRC_DIR = pymbrewclient
TEST_DIR = tests
DIST_DIR = dist
COV_REPORT_DIR = htmlcov

# Default target
.PHONY: all
all: test

# Install dependencies
.PHONY: install
install:
    $(PIP) install --upgrade pip
    $(PIP) install -r $(REQ_FILE)
    $(PIP) install pytest coverage

# Run tests with coverage
.PHONY: test
test:
    $(COVERAGE) run -m $(PYTEST)
    $(COVERAGE) report
    $(COVERAGE) xml
    $(COVERAGE) html

# Clean up coverage and build artifacts
.PHONY: clean
clean:
    rm -rf $(COV_REPORT_DIR) $(DIST_DIR) .coverage coverage.xml

# Build the package
.PHONY: build
build:
    $(PYTHON) setup.py sdist bdist_wheel

# Run linting (optional)
.PHONY: lint
lint:
    flake8 $(SRC_DIR) $(TEST_DIR)

# Run all checks (tests + linting)
.PHONY: check
check: lint test

# Run semantic commit validation
.PHONY: validate-commit
validate-commit:
    git log -1 --pretty=%B | grep -E '^(feat|fix|chore|docs|style|refactor|perf|test|ci|build): .+' || exit 1