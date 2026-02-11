# Quick Start Guide - Abiyasa

## Installation

### From PyPI (Once Published)

```bash
pip install abiyasa
```

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/abiyasa.git
cd abiyasa

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## 5-Minute Quick Start

### 1. Import and Load Data

```python
import abiyasa

# Load first 5 items with GSPN encoding
data = abiyasa.load_data(encoder='GSPN', limit=5)

print(f"Loaded {len(data)} items")
```

### 2. Explore the Data

```python
# Look at first item
item = data[0]

print(f"Title: {item['title']}")
print(f"PDF: {item['pdf_path']}")
print(f"Font: {item.get('font_type', 'N/A')}")

# See encoded notation
if 'encoded_data' in item:
    for line in item['encoded_data'][:3]:
        print(f"Line {line['line']}: {line['encoded']}")
```

### 3. Use Different Encoders

```python
# Use Kepatihan notation system
data_kepatihan = abiyasa.load_data(
    encoder='GSPN',
    notation_system='kepatihan',
    limit=3
)
```

### 4. Work with Encoders Directly

```python
from abiyasa import GSPNEncoder

# Create encoder
encoder = GSPNEncoder(notation_system='balungan')

# Encode some sequences
print(encoder.encode("H I J"))      # Output: 123
print(encoder.encode("- - F F"))    # Output: 006a6a
```

## Common Use Cases

### Load Metadata Only (Fast)

```python
# Just load metadata, don't extract PDFs
metadata = abiyasa.load_data(
    extract_pdf=False,
    verbose=False
)
```

### Custom Cache Directory

```python
from abiyasa import GamelanDataset

# Use custom cache location
dataset = GamelanDataset(cache_dir='./my_cache')
data = dataset.load_data(encoder='GSPN')
```

### Process Encoded Data

```python
data = abiyasa.load_data(encoder='GSPN', limit=3)

for item in data:
    if 'encoded_data' in item:
        # Process each encoded line
        for line_data in item['encoded_data']:
            original = line_data['original']
            encoded = line_data['encoded']
            
            # Your processing here
            print(f"{original} → {encoded}")
```

### Get Dataset Information

```python
info = abiyasa.get_dataset_info()

print(f"Total items: {info['total_items']}")
print(f"Cache directory: {info['cache_directory']}")
print(f"Available encoders: {info['available_encoders']}")
```

## Next Steps

1. **Read the Full Documentation**: See README.md for detailed usage
2. **Explore Examples**: Check `examples/basic_usage.py`
3. **Understand Architecture**: Read ARCHITECTURE.md
4. **Contribute**: See CONTRIBUTING.md for guidelines

## Troubleshooting

### PDFs Not Downloading

```python
# Enable verbose mode to see what's happening
data = abiyasa.load_data(verbose=True)

# Or manually check cache
from pathlib import Path
cache = Path.home() / '.abiyasa' / 'data'
print(f"Cache location: {cache}")
print(f"Files: {list(cache.glob('*.pdf'))}")
```

### Import Errors

```bash
# Make sure package is installed
pip list | grep abiyasa

# Reinstall if needed
pip install --force-reinstall -e .
```

### Missing Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Or individual packages
pip install pandas requests pdfplumber pymupdf fonttools
```

## Getting Help

- 📖 [Full Documentation](README.md)
- 🏗️ [Architecture Guide](ARCHITECTURE.md)
- 🤝 [Contributing Guide](CONTRIBUTING.md)
- 🐛 [Issue Tracker](https://github.com/yourusername/abiyasa/issues)

Happy encoding! 🎵
