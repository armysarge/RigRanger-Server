# Contributing to RigRanger Server

Thank you for your interest in contributing to RigRanger Server! We welcome contributions from everyone, whether you're fixing a typo, adding a feature, or reporting a bug.

## Getting Started

1. **Fork the Repository**: Start by forking the repository on GitHub.

2. **Clone Your Fork**: Clone your fork to your local machine.
   ```bash
   git clone https://github.com/YOUR-USERNAME/RigRanger-Server.git
   cd RigRanger-Server
   ```

3. **Install Dependencies**: Install the required dependencies.
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a Branch**: Create a new branch for your feature or bug fix.
   ```bash
   git checkout -b feature/your-feature-name
   ```

5. **Make Your Changes**: Implement your changes, following the coding guidelines below.

6. **Test Your Changes**: Run the tests to ensure your changes don't break anything.
   ```bash
   python run_tests.py
   ```

7. **Commit Your Changes**: Commit your changes with a clear and descriptive commit message.
   ```bash
   git commit -m "Add feature: your feature description"
   ```

8. **Push to Your Fork**: Push your changes to your fork on GitHub.
   ```bash
   git push origin feature/your-feature-name
   ```

9. **Submit a Pull Request**: Go to the original repository on GitHub and submit a pull request.

## Coding Guidelines

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines.
- Use 4 spaces for indentation (not tabs).
- Use docstrings for all modules, classes, and functions.
- Include type hints for function parameters and return values.
- Keep line length to a maximum of 100 characters.
- Use meaningful variable and function names.

### Documentation

- Update the documentation if you change functionality.
- Document new features in the appropriate section of the documentation.
- Use Markdown for documentation.

### Testing

- Add tests for new features.
- Make sure all tests pass before submitting a pull request.
- Aim for good test coverage of your code.

## Pull Request Process

1. Update the README.md or documentation with details of changes, if relevant.
2. Make sure all tests pass.
3. Update the version number in relevant files if applicable, following [semantic versioning](https://semver.org/).
4. Your pull request will be reviewed by the maintainers, who may suggest changes or improvements.
5. Once your pull request is approved, it will be merged into the main branch.

## Bug Reports and Feature Requests

- Use the GitHub issue tracker to report bugs or request features.
- For bugs, describe the issue clearly and include steps to reproduce it.
- For feature requests, describe the feature and why it would be valuable.

## Code of Conduct

Please note that this project adheres to a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to abide by its terms.

## License

By contributing to RigRanger Server, you agree that your contributions will be licensed under the same [MIT License](LICENSE) that covers the project.

Thank you for your contribution!
