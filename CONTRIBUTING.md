# Contributing to Fylax

Thank you for your interest in contributing to Fylax! We welcome contributions from everyone and appreciate your help in making this project better.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic familiarity with Python and GUI development

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Fylax.git
   cd Fylax
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
5. **Test the installation**:
   ```bash
   python src/fylax/gui.py
   ```

## 🎯 How to Contribute

### 🐛 Reporting Bugs

Before creating a bug report, please check if the issue already exists in our [issue tracker](https://github.com/JohnTocci/Fylax/issues).

When creating a bug report, please include:

- **Title**: Clear, descriptive summary
- **Description**: Detailed explanation of the problem
- **Steps to reproduce**: Step-by-step instructions
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: OS, Python version, Fylax version
- **Screenshots**: If applicable
- **Error logs**: Any relevant error messages

### 💡 Suggesting Features

We love new ideas! When suggesting a feature:

- **Search existing issues** to avoid duplicates
- **Use a clear title** that describes the feature
- **Provide context**: Why is this feature needed?
- **Describe the solution**: How should it work?
- **Consider alternatives**: What other approaches might work?

### 🔧 Contributing Code

#### Types of Contributions

We welcome:
- Bug fixes
- New features
- Performance improvements
- Documentation improvements
- Test coverage improvements
- Code refactoring

#### Development Workflow

1. **Create a branch** for your contribution:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes** following our coding standards

3. **Test your changes**:
   ```bash
   # Run the application to test functionality
   python src/fylax/gui.py
   
   # Test edge cases and error scenarios
   # Ensure existing functionality still works
   ```

4. **Format your code**:
   ```bash
   # Install development tools (if not already installed)
   pip install black isort flake8 mypy
   
   # Format code
   black fylax/
   isort fylax/
   
   # Check for issues
   flake8 fylax/
   mypy fylax/
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new file organization rule type"
   # or
   git commit -m "fix: resolve duplicate detection memory issue"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request** on GitHub

#### Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Build process, auxiliary tools, etc.

Examples:
```
feat: add support for regex patterns in advanced rules
fix: resolve crash when organizing empty folders
docs: update installation instructions for macOS
style: format code according to Black standards
refactor: simplify duplicate detection algorithm
test: add unit tests for profile management
chore: update dependencies to latest versions
```

## 📝 Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some specific preferences:

- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Imports**: Use `isort` for import organization
- **Type hints**: Use type hints for all public functions

### Code Organization

```
fylax/
├── gui.py          # Main GUI application
├── main.py         # Core organization engine
├── __init__.py     # Package initialization
└── utils/          # Utility modules (if needed)
```

### Documentation

- **Docstrings**: Use Google-style docstrings for all public functions and classes
- **Comments**: Explain complex logic and business decisions
- **Type hints**: Include type hints for better code clarity

Example:
```python
def organize_folder(
    folder_path: str,
    profile_name: Optional[str] = None,
    mode: str = "move",
    dry_run: bool = False
) -> Dict[str, int]:
    """Organize files in a folder based on configured rules.
    
    Args:
        folder_path: Path to the folder to organize
        profile_name: Name of the profile to use (None for active profile)
        mode: Organization mode ('move' or 'copy')
        dry_run: If True, only simulate the organization
        
    Returns:
        Dictionary with counts of moved, copied, skipped, and error files
        
    Raises:
        ValueError: If folder_path doesn't exist or profile is invalid
    """
```

## 🧪 Testing

### Manual Testing

Always test your changes manually:

1. **Basic functionality**: Ensure core features work
2. **Edge cases**: Test with empty folders, special characters, etc.
3. **Error handling**: Test error scenarios
4. **Cross-platform**: Test on different operating systems if possible

### Test Scenarios

Key scenarios to test:
- Organizing files with basic rules
- Advanced rule patterns
- Dry-run mode functionality
- Undo operations
- Profile switching
- Duplicate detection
- Error handling (permissions, missing files, etc.)

## 📚 Documentation

### README Updates

When adding new features, update the README:
- Add to feature list if it's a major feature
- Update configuration examples if needed
- Add to troubleshooting if common issues arise

### Code Documentation

- Keep docstrings up to date
- Document complex algorithms or business logic
- Update type hints when changing function signatures

## 🔍 Code Review Process

### Pull Request Guidelines

When submitting a PR:

1. **Clear title** describing the change
2. **Detailed description** explaining:
   - What changes were made
   - Why they were necessary
   - How to test the changes
3. **Link related issues** using keywords like "Fixes #123"
4. **Screenshots** for UI changes
5. **Test instructions** for reviewers

### Review Criteria

We review PRs for:
- **Functionality**: Does it work as intended?
- **Code quality**: Is it readable and maintainable?
- **Performance**: Does it impact app performance?
- **Compatibility**: Does it work across platforms?
- **Documentation**: Are changes properly documented?

## 🏆 Recognition

Contributors are recognized in:
- GitHub contributors list
- README acknowledgments
- Release notes for significant contributions

## 🤝 Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help newcomers learn and contribute
- Focus on what's best for the community

### Communication

- **GitHub Issues**: For bug reports and feature requests
- **Pull Requests**: For code contributions
- **GitHub Discussions**: For questions and general discussion

## 📞 Getting Help

If you need help with contributing:

1. Check existing documentation and issues
2. Ask in [GitHub Discussions](https://github.com/JohnTocci/Fylax/discussions)
3. Contact the maintainers directly

## 🙏 Thank You

Every contribution, no matter how small, helps make Fylax better for everyone. Thank you for taking the time to contribute!

---

Happy coding! 🚀