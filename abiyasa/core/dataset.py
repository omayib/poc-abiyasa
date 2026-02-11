"""
Core dataset loading and management functionality.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import warnings

from ..encoders import BaseEncoder, GSPNEncoder, QAPEncoder
from ..extractors.font_parser import parse_pdf_font
from ..extractors.line_extractor import extract_kepatihan_from_pdf
from ..utils.downloader import download_gamelan_file


class GamelanDataset:
    """
    Main class for loading and managing Gamelan music datasets.
    
    This class handles:
    - Loading dataset metadata from JSON
    - Downloading PDF files
    - Extracting notation from PDFs
    - Encoding notation to various formats (GSPN, QAP, etc.)
    """
    
    def __init__(
        self,
        dataset_path: Optional[str] = None,
        cache_dir: Optional[str] = None,
        auto_download: bool = True
    ):
        """
        Initialize the Gamelan dataset.
        
        Args:
            dataset_path: Path to dataset JSON file. If None, uses bundled dataset.
            cache_dir: Directory to cache downloaded PDFs. Defaults to ~/.abiyasa/data
            auto_download: Whether to automatically download missing PDFs
        """
        if dataset_path is None:
            # Use bundled dataset
            dataset_path = Path(__file__).parent.parent / 'data' / 'dataset_gamelan.json'
        
        self.dataset_path = Path(dataset_path)
        
        if cache_dir is None:
            cache_dir = Path.home() / '.abiyasa' / 'data'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.auto_download = auto_download
        self.metadata = self._load_metadata()
        self._encoder_registry = {
            'GSPN': GSPNEncoder,
            'QAP': QAPEncoder,
        }
    
    def _load_metadata(self) -> List[Dict[str, Any]]:
        """Load dataset metadata from JSON file."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {self.dataset_path}\n"
                "Please ensure the package is properly installed."
            )
        
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_encoder(self, encoder_name: str, notation_system: str = 'balungan') -> BaseEncoder:
        """
        Get an encoder instance by name.
        
        Args:
            encoder_name: Name of the encoder ('GSPN', 'QAP', etc.)
            notation_system: Notation system to use ('balungan' or 'kepatihan')
            
        Returns:
            Encoder instance
            
        Raises:
            ValueError: If encoder name is not recognized
        """
        encoder_name = encoder_name.upper()
        
        if encoder_name not in self._encoder_registry:
            available = ', '.join(self._encoder_registry.keys())
            raise ValueError(
                f"Unknown encoder: {encoder_name}. "
                f"Available encoders: {available}"
            )
        
        encoder_class = self._encoder_registry[encoder_name]
        return encoder_class(notation_system=notation_system)
    
    def load_data(
        self,
        encoder: str = 'GSPN',
        notation_system: str = 'balungan',
        extract_pdf: bool = True,
        limit: Optional[int] = None,
        verbose: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Load and encode gamelan dataset.
        
        Args:
            encoder: Encoder to use ('GSPN', 'QAP', etc.)
            notation_system: Notation system ('balungan' or 'kepatihan')
            extract_pdf: Whether to extract notation from PDFs
            limit: Maximum number of items to load (None for all)
            verbose: Whether to print progress information
            
        Returns:
            List of dictionaries containing:
                - title: Song title
                - filename: PDF filename
                - pdf_path: Local path to PDF
                - lines: Line specification
                - font_type: Detected font type
                - encoded_data: Encoded notation (if extract_pdf=True)
                - metadata: Additional metadata from dataset
        """
        encoder_instance = self.get_encoder(encoder, notation_system)
        
        results = []
        items = self.metadata[:limit] if limit else self.metadata
        total = len(items)
        
        for idx, item in enumerate(items, 1):
            if verbose:
                print(f"\n[{idx}/{total}] Processing: {item['title']}")
            
            try:
                result = self._process_item(item, encoder_instance, extract_pdf, verbose)
                results.append(result)
            except Exception as e:
                if verbose:
                    print(f"  ✗ Error processing {item['title']}: {e}")
                warnings.warn(f"Failed to process {item['title']}: {e}")
                continue
        
        if verbose:
            print(f"\n✓ Successfully loaded {len(results)}/{total} items")
        
        return results
    
    def _process_item(
        self,
        item: Dict[str, Any],
        encoder: BaseEncoder,
        extract_pdf: bool,
        verbose: bool
    ) -> Dict[str, Any]:
        """
        Process a single dataset item.
        
        Args:
            item: Dataset item metadata
            encoder: Encoder instance to use
            extract_pdf: Whether to extract and encode PDF content
            verbose: Whether to print progress
            
        Returns:
            Processed item dictionary
        """
        filename = f"{item['filename']}.pdf"
        url = item['dataset_url']
        lines_spec = item.get('lines', '')
        
        # Download PDF if needed
        pdf_path = self.cache_dir / filename
        
        if not pdf_path.exists() and self.auto_download:
            if verbose:
                print(f"  ⬇ Downloading from {url}")
            download_gamelan_file(url, pdf_path)
        elif not pdf_path.exists():
            raise FileNotFoundError(
                f"PDF not found: {pdf_path}\n"
                "Set auto_download=True to download automatically."
            )
        
        result = {
            'title': item['title'],
            'filename': item['filename'],
            'pdf_path': str(pdf_path),
            'lines': lines_spec,
            'metadata': {
                'identifier': item.get('identifier', {}),
                'used_by': item.get('used_by', []),
            }
        }
        
        # Extract and encode PDF content if requested
        if extract_pdf and lines_spec:
            if verbose:
                print(f"  📄 Extracting notation from PDF...")
            
            # Detect font type
            font_info = parse_pdf_font(str(pdf_path))
            if font_info:
                result['font_type'] = font_info['font_type']
                
                # Update encoder notation system if needed
                if font_info['font_type'] in ['kepatihan', 'balungan']:
                    encoder.notation_system = font_info['font_type']
            
            # Extract lines
            extraction = extract_kepatihan_from_pdf(str(pdf_path), lines_spec)
            
            if extraction:
                encoded_data = []
                
                for page in extraction.get('pages', []):
                    for line_no, content in page.get('lines', []):
                        # Encode the notation
                        try:
                            encoded = encoder.encode(content)
                            encoded_data.append({
                                'page': page.get('page_number'),
                                'line': line_no,
                                'original': content,
                                'encoded': encoded
                            })
                            
                            if verbose:
                                print(f"    Page {page.get('page_number')} | Line {line_no}: {content[:50]}...")
                        except Exception as e:
                            warnings.warn(f"Failed to encode line {line_no}: {e}")
                
                result['encoded_data'] = encoded_data
                
                if verbose:
                    print(f"  ✓ Encoded {len(encoded_data)} lines")
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the dataset.
        
        Returns:
            Dictionary containing dataset statistics
        """
        return {
            'total_items': len(self.metadata),
            'cache_directory': str(self.cache_dir),
            'cached_pdfs': len(list(self.cache_dir.glob('*.pdf'))),
            'available_encoders': list(self._encoder_registry.keys()),
        }
    
    def __len__(self) -> int:
        """Return the number of items in the dataset."""
        return len(self.metadata)
    
    def __repr__(self) -> str:
        """String representation of the dataset."""
        return f"GamelanDataset(items={len(self)}, cache_dir='{self.cache_dir}')"
