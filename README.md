# Abiyasa 🎵

A Python package for Gamelan music notation processing and encoding.

Abiyasa provides tools for loading, extracting, and encoding traditional Javanese Gamelan music notation from PDF files into various computational formats like GSPN (Gendhing Scientific Pitch Notation).

## Features

- 📄 **PDF Extraction**: Extract gamelan notation from PDF files
- 🎼 **Multiple Notation Systems**: Support for both Balungan and Kepatihan notation
- 🔢 **Encoding Strategies**: Convert notation to GSPN and other formats
- 📦 **Easy to Use**: Simple API for loading and processing datasets
- 🚀 **Extensible**: Easy to add new encoders and notation systems

## Installation

```bash
pip install abiyasa
```

### Development Installation

```bash
git clone https://github.com/yourusername/abiyasa.git
cd abiyasa
pip install -e .
```

## Quick Start

```python
import abiyasa

# Load dataset with GSPN encoding
data = abiyasa.load_data(encoder='GSPN', limit=5)

# Process the results
for item in data:
    print(f"Title: {item['title']}")
    print(f"Encoded: {item['encoded_data'][0]['encoded']}")
```

## Usage Examples

### Basic Usage

```python
import abiyasa

# Load entire dataset
data = abiyasa.load_data(encoder='GSPN')

# Load with specific notation system
data = abiyasa.load_data(
    encoder='GSPN',
    notation_system='kepatihan',
    limit=10
)

# Load metadata only (no PDF extraction)
metadata = abiyasa.load_data(extract_pdf=False)
```

### Advanced Usage

```python
from abiyasa import GamelanDataset, GSPNEncoder

# Create dataset instance with custom cache directory
dataset = GamelanDataset(cache_dir='./my_cache')

# Load data with custom settings
data = dataset.load_data(
    encoder='GSPN',
    notation_system='balungan',
    extract_pdf=True,
    limit=20,
    verbose=True
)

# Get dataset statistics
stats = dataset.get_statistics()
print(f"Total items: {stats['total_items']}")
print(f"Cached PDFs: {stats['cached_pdfs']}")

# Use encoder directly
encoder = GSPNEncoder(notation_system='balungan')
encoded = encoder.encode("- - - - F F")
print(encoded)  # Output: 00006a6a
```

### Working with Encoded Data

```python
import abiyasa

# Load and process data
data = abiyasa.load_data(encoder='GSPN', limit=3)

for item in data:
    print(f"\n{'='*60}")
    print(f"Title: {item['title']}")
    print(f"Font Type: {item.get('font_type', 'N/A')}")
    
    # Process encoded lines
    if 'encoded_data' in item:
        for line_data in item['encoded_data']:
            print(f"\nPage {line_data['page']} | Line {line_data['line']}")
            print(f"Original: {line_data['original']}")
            print(f"Encoded:  {line_data['encoded']}")
```

## Encoders

### GSPN (Gendhing Scientific Pitch Notation)

GSPN format: **T + W + V + G**

- **T**: Note number (0-7, where 0 is rest)
- **W**: Octave/register (empty=middle, a=low, b=high)
- **V**: Note value (empty=1, A=1/2, B=1/4)
- **G**: Legato (empty=none, x=start, y=end)

```python
from abiyasa import GSPNEncoder

encoder = GSPNEncoder(notation_system='balungan')

# Encode sequences
print(encoder.encode("- - - -"))      # Output: 0000
print(encoder.encode("F F"))          # Output: 6a6a
print(encoder.encode("H I J"))        # Output: 123
print(encoder.encode("-_ _F_"))       # Output: 0A6aA
```

### QAP (Quantized Audio Pitch)

*Coming soon! QAP encoder is currently under development.*

## Notation Systems

### Balungan Notation

Western-style uppercase letters representing gamelan notes:

- **Low octave**: C, D, E, F, G (3a, 4a, 5a, 6a, 7a)
- **Middle octave**: H, I, J, K, L, M, N (1, 2, 3, 4, 5, 6, 7)
- **High octave**: O, P, Q, R, S, T (1b, 2b, 3b, 4b, 5b, 6b)
- **Rest**: - (dash)

### Kepatihan Notation

Traditional Javanese notation system:

- **Low octave**: e, t, y, u (3a, 5a, 6a, 7a)
- **Middle octave**: 1, 2, 3, 4, 5, 6, 7
- **High octave**: !, @, #, %, ^ (1b, 2b, 3b, 5b, 6b)
- **Rest**: . (period)

## API Reference

### Main Functions

#### `abiyasa.load_data(encoder='GSPN', **kwargs)`

Load and encode gamelan dataset.

**Parameters:**
- `encoder` (str): Encoder to use ('GSPN', 'QAP')
- `notation_system` (str): 'balungan' or 'kepatihan'
- `extract_pdf` (bool): Whether to extract notation from PDFs
- `limit` (int): Maximum number of items to load
- `verbose` (bool): Print progress information
- `cache_dir` (str): Directory to cache PDFs

**Returns:** List of dictionaries with processed data

#### `abiyasa.get_dataset_info()`

Get dataset statistics and information.

**Returns:** Dictionary with dataset metadata

### Classes

#### `GamelanDataset`

Main class for dataset management.

```python
dataset = GamelanDataset(
    dataset_path=None,      # Path to dataset JSON
    cache_dir=None,         # Cache directory
    auto_download=True      # Auto-download PDFs
)
```

**Methods:**
- `load_data(encoder, **kwargs)`: Load and encode data
- `get_encoder(encoder_name, notation_system)`: Get encoder instance
- `get_statistics()`: Get dataset statistics

#### `GSPNEncoder`

GSPN encoding/decoding.

```python
encoder = GSPNEncoder(notation_system='balungan')
encoded = encoder.encode(sequence)
```

**Methods:**
- `encode(sequence)`: Encode notation to GSPN
- `decode(encoded)`: Decode GSPN to notation (not yet implemented)
- `get_info()`: Get encoder information

## Dataset Format

The package includes a curated dataset of Gamelan music in JSON format:

```json
[
  {
    "title": "Gending Title",
    "filename": "file_identifier",
    "dataset_url": "https://...",
    "lines": "p1:1-5,p2:3-7",
    "identifier": {...},
    "used_by": [...]
  }
]
```

## Contributing

Contributions are welcome! Here are some ways you can contribute:

1. **Add new encoders**: Implement QAP or other encoding strategies
2. **Improve extractors**: Enhance PDF extraction accuracy
3. **Add datasets**: Contribute more gamelan music datasets
4. **Fix bugs**: Report and fix issues
5. **Documentation**: Improve docs and examples

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/abiyasa.git
cd abiyasa

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
black abiyasa/
```

## Citation

If you use this package in academic work, please cite:

Reference to GSPN format:
```
Syarif, A. M., Azhari, A., Suprapto, S., & Hastuti, K. (2020).
Human and computation-based musical representation for Gamelan music.
Malaysian Journal of Music, 9, 82-100.
```

## License

MIT License - see LICENSE file for details

## Acknowledgments

- GSPN format based on research by Syarif et al. (2020)
- Gamelan notation systems from traditional Javanese music theory
- Dataset compiled from various sources (see dataset metadata)

## Support

- 📖 [Documentation](https://abiyasa.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/yourusername/abiyasa/issues)
- 💬 [Discussions](https://github.com/yourusername/abiyasa/discussions)

---

Made with ❤️ for Gamelan music preservation and research
