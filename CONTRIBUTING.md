# Contributing to Asas

Thank you for your interest in contributing to Asas! We welcome contributions from the community to help make this API client builder even better.

## Getting Started

1. **Fork the Repository**: Create your own fork of the project on GitHub.
2. **Clone the Repository**:
   ```bash
   git clone https://github.com/YourUsername/asas-py.git
   cd asas-py
   ```
3. **Set Up Development Environment**:
   We use a `Makefile` to simplify setup. Run the following command to install dependencies and set up git hooks:
   ```bash
   make dev-install
   ```

## Development Workflow

### Coding Standards
We aim for high-quality, readable code. Please adhere to the following:
- **Style**: We use [Black](https://github.com/psf/black) for code formatting and [isort](https://github.com/PyCQA/isort) for import sorting.
- **Typing**: Use Python type hints throughout the codebase.
- **Linting**: Before committing, ensure your code passes all linting checks:
  ```bash
  make lint
  ```

### Making Changes
1. **Create a Branch**: Create a new branch for your feature or bug fix.
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Write Code**: Implement your changes.
3. **Format Your Code**:
   ```bash
   make format
   ```
4. **Commit Your Changes**: Follow clear and concise commit message conventions.
5. **Push and Pull Request**: Push your branch to your fork and submit a Pull Request (PR) to the main repository.

## Feedback and Bug Reports
If you find a bug or have a suggestion, please open an issue on the GitHub repository. Provide as much detail as possible, including steps to reproduce for bugs.

## License
By contributing to Asas, you agree that your contributions will be licensed under the project's MIT License.
