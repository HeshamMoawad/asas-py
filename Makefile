.PHONY: dev-install format lint build clean help

help:
	@echo "Available commands:"
	@echo "  dev-install  - Install development dependencies and setup pre-commit"
	@echo "  format       - Format code with black and isort"
	@echo "  lint         - Run pre-commit hooks on all files"
	@echo "  build        - Build the package"
	@echo "  clean        - Remove build artifacts"

dev-install:
	pip install -r requirements.txt
	pip install -e .
	pre-commit install

format:
	black .
	isort .

lint:
	pre-commit run --all-files

build:
	python -m build

clean:
	rm -rf build/ dist/ *.egg-info/
