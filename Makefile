.PHONY: dev-install format lint test type-check build docs-serve docs-build clean help

help:
	@echo "Available commands:"
	@echo "  dev-install  - Install development dependencies and setup pre-commit"
	@echo "  format       - Format code with black and isort"
	@echo "  lint         - Run pre-commit hooks on all files"
	@echo "  test         - Run tests with coverage"
	@echo "  type-check   - Run mypy for type checking"
	@echo "  build        - Build the package"
	@echo "  docs-serve   - Serve the documentation"
	@echo "  docs-build   - Build the documentation"
	@echo "  clean        - Remove build artifacts"

dev-install:
	pip install -r requirements.txt
	pip install mkdocs-material mkdocs-static-i18n
	pre-commit install

format:
	black .
	isort .

lint:
	pre-commit run --all-files

test:
	pytest --cov=asas tests/

type-check:
	mypy asas/

build:
	python -m build

docs-serve:
	mkdocs serve

docs-deploy:
	mkdocs build
	mkdocs gh-deploy

clean:
	rm -rf build/ dist/ *.egg-info/ site/
