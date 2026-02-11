"""
Abiyasa - A Python package for Gamelan music notation processing and encoding

This package provides tools for:
- Loading gamelan music datasets
- Extracting notation from PDF files
- Encoding notation in various formats (GSPN, QAP, etc.)
- Working with both Balungan and Kepatihan notation systems

Example usage:
    >>> import abiyasa
    >>> 
    >>> # Load dataset with GSPN encoding
    >>> data = abiyasa.load_data(encoder='GSPN')
    >>> 
    >>> # Or use the dataset class directly
    >>> dataset = abiyasa.GamelanDataset()
    >>> data = dataset.load_data(encoder='GSPN', limit=10)
"""

from .core import GamelanDataset
from .encoders import BaseEncoder, GSPNEncoder, QAPEncoder

__version__ = '0.1.0'
__author__ = 'Your Name'
__all__ = [
    'load_data',
    'GamelanDataset',
    'BaseEncoder',
    'GSPNEncoder',
    'QAPEncoder',
]


# Global dataset instance for convenience
_default_dataset = None


def load_data(
    encoder: str = 'GSPN',
    notation_system: str = 'balungan',
    extract_pdf: bool = True,
    limit: int = None,
    verbose: bool = True,
    cache_dir: str = None,
):
    """
    Convenience function to load gamelan dataset with encoding.
    
    This is the main entry point for most users. It creates a GamelanDataset
    instance and loads the data with the specified encoder.
    
    Args:
        encoder: Encoder to use ('GSPN', 'QAP', etc.). Default: 'GSPN'
        notation_system: Notation system ('balungan' or 'kepatihan'). Default: 'balungan'
        extract_pdf: Whether to extract and encode notation from PDFs. Default: True
        limit: Maximum number of items to load (None for all). Default: None
        verbose: Whether to print progress information. Default: True
        cache_dir: Directory to cache downloaded PDFs. Default: ~/.abiyasa/data
        
    Returns:
        List of dictionaries containing processed gamelan music data
        
    Examples:
        >>> # Load first 5 items with GSPN encoding
        >>> data = abiyasa.load_data(encoder='GSPN', limit=5)
        >>> 
        >>> # Load all data without PDF extraction (metadata only)
        >>> metadata = abiyasa.load_data(extract_pdf=False, verbose=False)
        >>> 
        >>> # Use Kepatihan notation system
        >>> data = abiyasa.load_data(
        ...     encoder='GSPN',
        ...     notation_system='kepatihan',
        ...     limit=10
        ... )
    """
    global _default_dataset
    
    if _default_dataset is None or cache_dir is not None:
        _default_dataset = GamelanDataset(cache_dir=cache_dir)
    
    return _default_dataset.load_data(
        encoder=encoder,
        notation_system=notation_system,
        extract_pdf=extract_pdf,
        limit=limit,
        verbose=verbose
    )


def get_dataset_info():
    """
    Get information about the gamelan dataset.
    
    Returns:
        Dictionary containing dataset statistics and information
        
    Example:
        >>> info = abiyasa.get_dataset_info()
        >>> print(f"Total items: {info['total_items']}")
    """
    global _default_dataset
    
    if _default_dataset is None:
        _default_dataset = GamelanDataset()
    
    return _default_dataset.get_statistics()
