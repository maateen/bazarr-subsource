# Contributing to Bazarr SubSource Integration

> ⚠️ **Active Development**: This project is under active development. All changes are merged directly to the `main` branch.

Thank you for your interest in contributing to this project! We welcome contributions from the community.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this standard of behavior:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## AI-Generated Code Policy

This project welcomes contributions that use AI assistance for code generation, but with the following requirements:

- **Human Review Required**: All AI-generated code must be thoroughly reviewed by humans before submission
- **Understanding Required**: Contributors must understand the code they submit, regardless of how it was generated
- **Testing Required**: AI-generated code must include appropriate tests and documentation
- **Disclosure Encouraged**: While not required, contributors are encouraged to mention when AI tools were used
- **Quality Standards**: AI-generated code must meet the same quality standards as human-written code

Part of this existing codebase was generated with AI assistance but has been reviewed and validated by humans.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to see if the problem has already been reported. When you create a bug report, please include as many details as possible:

1. **Use a clear and descriptive title**
2. **Describe the exact steps to reproduce the problem**
3. **Provide specific examples** to demonstrate the steps
4. **Describe the behavior you observed** and what you expected instead
5. **Include screenshots** if applicable
6. **Include your environment details**:
   - OS and version
   - Python version
   - Bazarr version
   - Tool version/commit

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

1. **Use a clear and descriptive title**
2. **Provide a detailed description** of the suggested enhancement
3. **Explain why this enhancement would be useful**
4. **List some examples** of how the enhancement would be used

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the coding standards
3. **Add tests** if you're adding functionality
4. **Update documentation** if needed
5. **Ensure the test suite passes**
6. **Make sure your code lints** using pre-commit hooks
7. **Create a pull request**

## Development Setup

### Prerequisites

- Python 3.7 or higher
- Git
- A text editor or IDE

### Setting Up Your Development Environment

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/maateen/bazarr-subsource.git
   cd bazarr-subsource
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pre-commit
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

5. **Run the tests**:
   ```bash
   python -c "import bazarr; import subsource; import tracking; import config; import utils; print('All imports successful')"
   ```

### Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards

3. **Run pre-commit checks**:
   ```bash
   pre-commit run --all-files
   ```

4. **Test your changes**:
   ```bash
   python run.py  # Test basic functionality
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add your descriptive commit message"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request** from your fork to the main repository

### AI-Generated Code Contributions

When submitting AI-generated code:

1. **Review Thoroughly**: Understand every line of the generated code
2. **Test Comprehensively**: Ensure the code works as expected with appropriate tests
3. **Document Clearly**: Add clear comments and documentation
4. **Follow Standards**: Ensure the code meets project coding standards
5. **Mention in PR**: Optionally mention AI assistance in your pull request description

Example PR description:
```
## Summary
Add new subtitle validation feature

## Changes
- Implemented subtitle format validation
- Added corresponding unit tests
- Updated documentation

## Notes
Parts of this implementation used AI assistance for boilerplate code generation,
but all code has been reviewed, tested, and validated.
```

## Coding Standards

### Python Style Guide

This project follows PEP 8 with some modifications:

- **Line length**: Maximum 88 characters (Black's default)
- **String quotes**: Use double quotes for strings
- **Import organization**: Use isort for import sorting
- **Code formatting**: Use Black for code formatting
- **Linting**: Use flake8 for code quality checks

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **Basic hooks**: Trailing whitespace, end of file, etc.

Run pre-commit manually:
```bash
pre-commit run --all-files
```

### Documentation

- **Docstrings**: Use Google-style docstrings for all functions and classes
- **Comments**: Write clear, concise comments for complex logic
- **README**: Update README.md if you add new features
- **Type hints**: Use type hints where appropriate

### Testing

While this project doesn't have a full test suite yet, please:

- **Test your changes** manually with different configurations
- **Verify imports** work correctly
- **Check error handling** with invalid inputs
- **Test with different Python versions** if possible

## Project Structure

```
bazarr-subsource/
├── run.py              # Main entry point
├── api/                # API clients
│   ├── __init__.py
│   ├── bazarr.py       # Bazarr API client
│   └── subsource.py    # SubSource API client
├── core/               # Core functionality
│   ├── __init__.py
│   ├── config.py       # Configuration management
│   └── tracking.py     # Search tracking system
├── utils.py            # Utility functions
├── requirements.txt    # Python dependencies
├── .pre-commit-config.yaml
├── .gitignore
├── README.md
├── LICENSE
├── SECURITY.md
├── CONTRIBUTING.md
└── .github/            # GitHub templates & workflows
    ├── workflows/
    │   └── ci.yml      # GitHub Actions workflow
    └── ISSUE_TEMPLATE/
```

## Commit Message Guidelines

Use clear and meaningful commit messages:

- **Use imperative mood**: "Add feature" not "Added feature"
- **Keep the first line under 50 characters**
- **Reference issues**: "Fix issue #123"
- **Be descriptive**: Explain what and why, not just what

Examples:
```
Add support for multiple SubSource languages
Fix rate limiting issue with SubSource API
Update README with installation instructions
Refactor configuration loading logic
```

## Areas for Contribution

We welcome contributions in these areas:

### Priority Areas
- **Testing**: Add unit tests and integration tests
- **Error Handling**: Improve error messages and recovery
- **Documentation**: Improve inline documentation and examples
- **Performance**: Optimize API calls and file operations

### Feature Ideas
- **GUI Interface**: Desktop application with GUI
- **Docker Support**: Containerized deployment
- **Additional Providers**: Support for other subtitle sources
- **Scheduling**: Built-in scheduler for automatic runs
- **Notifications**: Email/webhook notifications for downloads
- **Statistics**: Detailed download statistics and reporting

### Bug Fixes
- Check the [issues page](https://github.com/maateen/bazarr-subsource/issues) for reported bugs
- Look for issues tagged with "good first issue" or "help wanted"

## Getting Help

If you need help with development:

1. **Check the documentation** in README.md and code comments
2. **Search existing issues** and discussions
3. **Create a discussion** for questions about development
4. **Join the conversation** in existing issues

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- README acknowledgments section

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to make this project better! 🎉
