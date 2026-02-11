# Abiyasa Architecture Documentation

## Overview

Abiyasa is designed with a modular, extensible architecture that separates concerns into distinct layers:

1. **Core Layer**: Dataset management and orchestration
2. **Encoders Layer**: Encoding/decoding strategies
3. **Extractors Layer**: PDF parsing and content extraction
4. **Utils Layer**: Helper functions and utilities

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User API                             │
│  abiyasa.load_data()  │  GamelanDataset  │  GSPNEncoder   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│ Core Layer   │    │   Encoders   │      │  Extractors  │
│              │    │              │      │              │
│ - Dataset    │    │ - Base       │      │ - Font       │
│   Management │    │ - GSPN       │      │   Parser     │
│ - Orchestr.  │    │ - QAP        │      │ - Line       │
│              │    │              │      │   Extractor  │
└──────────────┘    └──────────────┘      └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                      ┌──────────────┐
                      │ Utils Layer  │
                      │              │
                      │ - Downloader │
                      │ - Notation   │
                      └──────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  Data Files  │
                      │              │
                      │ - JSON Data  │
                      │ - PDF Cache  │
                      └──────────────┘
```

## Component Details

### 1. Core Layer (`abiyasa/core/`)

#### GamelanDataset (`dataset.py`)

**Purpose**: Main orchestrator for dataset operations

**Key Responsibilities**:
- Load dataset metadata from JSON
- Manage PDF file cache
- Coordinate encoding process
- Handle encoder selection

**Key Methods**:
```python
__init__(dataset_path, cache_dir, auto_download)
load_data(encoder, notation_system, extract_pdf, limit, verbose)
get_encoder(encoder_name, notation_system)
get_statistics()
```

**Design Patterns**:
- **Facade Pattern**: Provides simple interface to complex subsystems
- **Factory Pattern**: Creates encoder instances via `get_encoder()`
- **Strategy Pattern**: Uses different encoders interchangeably

### 2. Encoders Layer (`abiyasa/encoders/`)

#### Base Encoder (`base.py`)

**Purpose**: Abstract interface for all encoders

**Key Features**:
- Defines common interface
- Enforces implementation of `encode()` and `decode()`
- Provides metadata methods

**Interface**:
```python
class BaseEncoder(ABC):
    @abstractmethod
    def encode(sequence: str) -> str
    
    @abstractmethod
    def decode(encoded: str) -> str
    
    @property
    @abstractmethod
    def name() -> str
```

#### GSPN Encoder (`gspn.py`)

**Purpose**: Converts notation to GSPN (Gendhing Scientific Pitch Notation)

**Key Features**:
- Supports Balungan and Kepatihan notation systems
- Handles note values (whole, half, quarter)
- Processes legato markers
- Manages octave information

**Encoding Process**:
1. Parse sequence into elements
2. Extract notes with values
3. Apply legato markers
4. Generate GSPN string

**Example**:
```
Input:  "ÎI J"
Parse:  [legato_start, note:I, note:J]
Extract: [note:2, note:3]
Legato:  [2x, 3y]
Output: "2x3y"
```

#### QAP Encoder (`qap.py`)

**Purpose**: Placeholder for future QAP encoding

**Status**: Not implemented (raises NotImplementedError)

### 3. Extractors Layer (`abiyasa/extractors/`)

#### Font Parser (`font_parser.py`)

**Purpose**: Extract and parse fonts from PDF files

**Key Features**:
- Detects Balungan/Kepatihan fonts
- Extracts glyph mappings
- Generates SVG paths for glyphs
- Handles both TTF and CFF formats

**Functions**:
```python
parse_pdf_font(pdf_path, output_dir)
extract_glyph_map(font_path, include_svg, max_glyphs)
extract_glyph_map_cff(font_path, include_svg)
detect_font_type(font_list)
```

#### Line Extractor (`line_extractor.py`)

**Purpose**: Extract specific lines from PDF files

**Key Features**:
- Supports page-specific extraction: `"p1:1-5,p2:3-7"`
- Supports line loops: `"1-5*2"` (repeat lines 1-5 twice)
- Supports bracket loops: `"[1-4,8-10]*2"`
- Preserves order and repetition

**Classes**:
```python
class LineFilter:
    parse_line_spec(line_spec)
    parse_bracket_loop(line_spec)
    filter_lines(lines, line_spec)
    parse_page_line_spec(line_spec)

extract_kepatihan_from_pdf(pdf_path, line_spec)
```

### 4. Utils Layer (`abiyasa/utils/`)

#### Downloader (`downloader.py`)

**Purpose**: Download PDF files from URLs

**Key Features**:
- HTTP download with timeout
- Local caching
- Force re-download option

**Function**:
```python
download_gamelan_file(url, local_path, timeout, force_download)
```

## Data Flow

### Loading Data with Encoding

```
1. User calls: abiyasa.load_data(encoder='GSPN', limit=5)
                          │
2. GamelanDataset initialized
                          │
3. Load metadata from JSON ──────────► dataset_gamelan.json
                          │
4. For each item:
   ├─► Check cache ──────────────────► ~/.abiyasa/data/
   ├─► Download if needed ───────────► HTTP request
   ├─► Detect font type ─────────────► Font Parser
   ├─► Extract lines ────────────────► Line Extractor
   ├─► Get encoder ──────────────────► GSPN Encoder
   └─► Encode sequences ─────────────► GSPN format
                          │
5. Return processed data ────────────► User
```

## Design Principles

### 1. Separation of Concerns
- Each module has a single, well-defined responsibility
- Clear boundaries between layers
- Minimal coupling between components

### 2. Extensibility
- Easy to add new encoders via inheritance
- Pluggable architecture for new features
- Open for extension, closed for modification

### 3. User-Friendly API
- Simple function: `abiyasa.load_data()`
- Progressive complexity: use classes for advanced needs
- Sensible defaults with configuration options

### 4. Performance
- Lazy loading: only download when needed
- Caching: reuse downloaded PDFs
- Optional extraction: metadata-only mode

### 5. Robustness
- Graceful error handling
- Warnings for non-critical issues
- Comprehensive validation

## Extension Points

### Adding a New Encoder

1. **Create encoder class**:
```python
from abiyasa.encoders.base import BaseEncoder

class MIDIEncoder(BaseEncoder):
    @property
    def name(self) -> str:
        return "MIDI"
    
    def encode(self, sequence: str) -> str:
        # Implementation
        pass
```

2. **Register in `__init__.py`**:
```python
from .midi import MIDIEncoder
__all__ = [..., 'MIDIEncoder']
```

3. **Add to dataset registry**:
```python
self._encoder_registry = {
    'GSPN': GSPNEncoder,
    'MIDI': MIDIEncoder,
}
```

### Adding a New Notation System

1. **Update encoder mappings**:
```python
CIPTONAN_SYSTEM = {
    # Add mappings
}
```

2. **Support in encoder**:
```python
if self.notation_system == 'ciptonan':
    note_map = self.CIPTONAN_SYSTEM
```

### Adding Dataset Features

Extend `GamelanDataset` with new methods:

```python
def export_to_midi(self, output_path):
    """Export dataset to MIDI files."""
    pass

def get_statistics_by_type(self):
    """Get detailed statistics."""
    pass
```

## File Organization

```
abiyasa/
├── abiyasa/              # Main package
│   ├── __init__.py       # Public API
│   ├── core/             # Core functionality
│   │   ├── __init__.py
│   │   └── dataset.py
│   ├── encoders/         # Encoding strategies
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── gspn.py
│   │   └── qap.py
│   ├── extractors/       # PDF extraction
│   │   ├── __init__.py
│   │   ├── font_parser.py
│   │   └── line_extractor.py
│   ├── utils/            # Utilities
│   │   ├── __init__.py
│   │   └── downloader.py
│   └── data/             # Data files
│       └── dataset_gamelan.json
├── tests/                # Test suite
├── examples/             # Usage examples
├── setup.py              # Installation
├── pyproject.toml        # Modern packaging
└── README.md             # Documentation
```

## Testing Strategy

### Unit Tests
- Test each encoder independently
- Mock external dependencies
- Test edge cases and error conditions

### Integration Tests
- Test full workflow: load → extract → encode
- Test with sample PDFs
- Verify end-to-end functionality

### Example Test Structure:
```python
def test_gspn_encoding():
    encoder = GSPNEncoder('balungan')
    assert encoder.encode("H I J") == "123"

def test_dataset_loading():
    dataset = GamelanDataset()
    data = dataset.load_data(limit=1)
    assert len(data) == 1
```

## Performance Considerations

### Caching Strategy
- PDFs cached in `~/.abiyasa/data/`
- Persistent across sessions
- Configurable cache directory

### Memory Management
- Stream large PDFs
- Process one item at a time
- Optional limit parameter

### Network Efficiency
- Check cache before downloading
- Configurable timeout
- Retry logic (future)

## Security Considerations

- Validate URLs before downloading
- Sanitize file paths
- Handle malformed PDFs gracefully
- No arbitrary code execution

## Future Enhancements

1. **More Encoders**: MIDI, MusicXML, ABC notation
2. **Audio Processing**: Generate audio from notation
3. **Visualization**: Render notation graphically
4. **Web API**: RESTful API for remote access
5. **Database Backend**: Support PostgreSQL/MongoDB
6. **Batch Processing**: Parallel processing of multiple files
7. **Cloud Storage**: S3/Google Cloud integration
8. **ML Features**: Pattern recognition, auto-encoding

## References

- GSPN Paper: Syarif et al. (2020), Malaysian Journal of Music
- Balungan Notation: Traditional Javanese music theory
- Kepatihan Notation: Javanese notation system
- PDF Processing: PyMuPDF, pdfplumber libraries
