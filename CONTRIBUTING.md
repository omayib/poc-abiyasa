# Contributing to Abiyasa

Thank you for your interest in contributing to Abiyasa! This document provides guidelines and instructions for contributing.

## Ways to Contribute

1. **Report Bugs**: Open an issue describing the bug and how to reproduce it
2. **Suggest Features**: Open an issue with your feature proposal
3. **Improve Documentation**: Submit PRs to improve README, docstrings, or examples
4. **Add Encoders**: Implement new encoding strategies (QAP, MIDI, etc.)
5. **Expand Dataset**: Contribute additional gamelan music datasets
6. **Fix Bugs**: Submit PRs fixing existing issues

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/abiyasa.git
cd abiyasa
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### 4. Run Tests

```bash
pytest tests/ -v
```

## Code Style

We follow PEP 8 and use Black for formatting:

```bash
# Format code
black abiyasa/

# Check formatting
black --check abiyasa/

# Lint code
flake8 abiyasa/

# Type checking
mypy abiyasa/
```

## Adding a New Encoder

To add a new encoding strategy:

1. Create a new file in `abiyasa/encoders/`:

```python
# abiyasa/encoders/my_encoder.py

from .base import BaseEncoder

class MyEncoder(BaseEncoder):
    @property
    def name(self) -> str:
        return "MyEncoder"
    
    def encode(self, sequence: str) -> str:
        # Your encoding logic
        pass
    
    def decode(self, encoded: str) -> str:
        # Your decoding logic
        pass
```

2. Register it in `abiyasa/encoders/__init__.py`:

```python
from .my_encoder import MyEncoder

__all__ = [..., 'MyEncoder']
```

3. Add tests in `tests/test_encoders.py`

4. Update documentation

## Pull Request Process

1. Create a new branch: `git checkout -b feature/my-feature`
2. Make your changes and commit: `git commit -m "Add my feature"`
3. Push to your fork: `git push origin feature/my-feature`
4. Open a Pull Request on GitHub
5. Ensure all tests pass
6. Wait for review

## Writing Tests

Tests should be placed in the `tests/` directory:

```python
import pytest
from abiyasa.encoders import MyEncoder

def test_my_encoder():
    encoder = MyEncoder(notation_system='balungan')
    result = encoder.encode("H I J")
    assert result == "expected_output"
```

Run tests with:

```bash
pytest tests/ -v --cov=abiyasa
```

## Documentation

- Add docstrings to all public functions and classes
- Follow Google-style docstring format
- Update README.md with new features
- Add examples to `examples/` directory

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.

Thank you for contributing! 🎵
