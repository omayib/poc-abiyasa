"""
Core dataset loading and management functionality.
"""

import json
import os
from importlib.metadata import metadata
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

    # Maps each dataset_name to the exact list of line-range keys to extract
    # from its used_by entry.  Keys vary per dataset:
    #   - Some datasets (BARISS_DSET) only have instrument-part PDFs and do
    #     NOT include the primary balungan 'lines' key.
    #   - Others (BORUSS_DSET, REBUNG_DSET) combine 'lines' with instrument parts.
    #   - Simple datasets (QAP_DSET, OVENS_DSET, …) only have 'lines'.
    #
    # To add a new dataset, append its entry here — no other code needs changing.
    DATASET_LINE_KEYS: Dict[str, List[str]] = {
        # Instrument-part PDFs only — balungan is NOT extracted for BARISS
        'BARISS_DSET': [
            'lines_kenong',
            'lines_kethuk',
            'lines_kempul',
            'lines_kempyang',
            'lines_suwuk',
            'lines_ageng',
        ],
        # Primary balungan + bonang parts
        'BORUSS_DSET': [
            'lines',
            'lines_barung',
            'lines_penerus',
        ],
        # Primary balungan + bonang barung
        'REBUNG_DSET': [
            'lines',
            'lines_barung',
        ],
        # Only primary balungan line
        'QAP_DSET':            ['lines'],
        'OVENS_DSET':          ['lines'],
        '35_GERONGAN_SM_DSET': ['lines'],
        '59_LADRANG_SM_DSET':  ['lines'],
        # Fallback for any dataset not explicitly listed above
        '__default__': ['lines'],
    }

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
            dataset_path = Path(__file__).parent.parent / 'data' / 'meta_dataset_gamelan.json'

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

    def _get_line_keys(self, dataset_name: Optional[str]) -> List[str]:
        """
        Return the ordered list of line-range keys for a given dataset_name.

        Looks up DATASET_LINE_KEYS; falls back to ['lines'] for unknown or
        None dataset names.

        Args:
            dataset_name: The dataset_name string from a used_by entry, or None.

        Returns:
            List of line-key strings (e.g. ['lines', 'lines_kenong', ...])
        """
        if dataset_name is None:
            return self.DATASET_LINE_KEYS['__default__']
        return self.DATASET_LINE_KEYS.get(dataset_name, self.DATASET_LINE_KEYS['__default__'])

    def load_data(
        self,
        encoder: str = 'GSPN',
        notation_system: str = 'balungan',
        extract_pdf: bool = True,
        limit: Optional[int] = None,
        verbose: bool = True,
        filter_dset: str = None
    ) -> List[Dict[str, Any]]:
        """
        Load and encode gamelan dataset.

        Args:
            encoder: Encoder to use ('GSPN', 'QAP', etc.)
            notation_system: Notation system ('balungan' or 'kepatihan')
            extract_pdf: Whether to extract notation from PDFs
            limit: Maximum number of items to load (None for all)
            verbose: Whether to print progress information
            filter_dset: If given, only load items used by this dataset and
                         resolve PDF/line metadata from the matching used_by entry.

        Returns:
            List of dictionaries containing:
                - title: Song title
                - filename: PDF filename (dataset-specific when filter_dset is set)
                - pdf_path: Local path to PDF
                - parts: Dict mapping each part name to its encoded line list.
                         e.g. {'lines': [...], 'lines_kenong': [...], ...}
                         Parts with an empty line spec in the JSON are omitted.
                - metadata: Additional metadata from dataset
        """
        encoder_instance = self.get_encoder(encoder, notation_system)

        results = []
        if filter_dset:
            print(f"filter dset on")
            items = [item for item in self.metadata
                     if any(usage.get('dataset_name') == filter_dset for usage in item.get('used_by', []))]
        else:
            items = self.metadata[:limit] if limit else self.metadata
        total = len(items)

        for idx, item in enumerate(items, 1):
            # print(f"items==> \n{json.dumps(item, indent=4)}")
            if verbose:
                print(f"\n[{idx}/{total}] Processing: {item['title']}")

            try:
                result = self._process_item(item, encoder_instance, extract_pdf, verbose, dataset_name=filter_dset)
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
        verbose: bool,
        dataset_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single dataset item.

        When ``dataset_name`` is provided the method resolves the PDF url,
        filename, and *all* part-specific line keys from the matching
        ``used_by`` entry.  Different datasets declare different sets of parts
        (e.g. BARISS_DSET has kenong/kethuk/… while REBUNG_DSET has barung);
        the ``DATASET_LINE_KEYS`` registry drives which keys are extracted so
        no dataset-specific branching is needed here.

        Args:
            item: Dataset item metadata
            encoder: Encoder instance to use
            extract_pdf: Whether to extract and encode PDF content
            verbose: Whether to print progress
            dataset_name: If provided, resolve pdf/lines from the matching
                          used_by entry and extract all registered parts.

        Returns:
            Processed item dictionary with a ``parts`` key that maps each
            part name (e.g. ``'lines'``, ``'lines_kenong'``) to its list of
            encoded line dicts.  Parts whose line spec is empty are omitted.
        """
        # ------------------------------------------------------------------
        # 1. Resolve source metadata (top-level item vs dataset-specific entry)
        # ------------------------------------------------------------------
        dataset_entry = None
        if dataset_name:
            dataset_entry = next(
                (u for u in item.get('used_by', []) if u.get('dataset_name') == dataset_name),
                None
            )
            if dataset_entry is None:
                raise ValueError(
                    f"No 'used_by' entry with dataset_name='{dataset_name}' "
                    f"found for item '{item['title']}'"
                )

        # Some used_by entries carry their own PDF (filename + dataset_url),
        # while others reuse the top-level item's PDF and only add line specs
        # or pre-computed sequences.  Fall back to the item-level values so
        # both cases are handled transparently.
        source = dataset_entry if dataset_entry is not None else item
        filename = f"{source.get('filename') or item['filename']}.pdf"
        url = source.get('dataset_url') or item['dataset_url']

        # ------------------------------------------------------------------
        # 2. Download PDF if needed
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # 3. Build base result
        # ------------------------------------------------------------------
        result = {
            'title': item['title'],
            'filename': source.get('filename') or item['filename'],
            'pdf_path': str(pdf_path),
            'metadata': {
                'identifier': item.get('identifier', {}),
                'used_by': item.get('used_by', []),
                # Expose the active dataset-specific entry for easy access
                **({'dataset_entry': dataset_entry} if dataset_entry is not None else {}),
            }
        }

        # ------------------------------------------------------------------
        # 4. Extract & encode each part defined for this dataset
        # ------------------------------------------------------------------
        if extract_pdf:
            print(f"extract_pdf {extract_pdf}")
            # Detect font type once per PDF — applies to all parts
            font_info = parse_pdf_font(str(pdf_path))
            if font_info and font_info.get('font_type') in ['kepatihan', 'balungan']:
                encoder.notation_system = font_info['font_type']
                result['font_type'] = font_info['font_type']

            # Look up which line keys this dataset declares
            line_keys = self._get_line_keys(dataset_name)
            parts: Dict[str, List[Dict[str, Any]]] = {}

            for key in line_keys:
                lines_spec = source.get(key, '').strip()
                # For the primary 'lines' key, fall back to the parent item's
                # value when the used_by entry leaves it empty.  Other keys
                # (lines_kenong, lines_barung, …) are dataset-specific and
                # have no meaningful parent-level equivalent to fall back to.
                if key == 'lines' and not lines_spec:
                    lines_spec = item.get('lines', '').strip()

                if not lines_spec:
                    # Part not annotated for this item — skip silently
                    if verbose:
                        print(f"  ↷ Skipping '{key}' (no line spec)")
                    continue

                if verbose:
                    print(f"  📄 Extracting part '{key}' (lines: {lines_spec}) …")

                extraction = extract_kepatihan_from_pdf(str(pdf_path), lines_spec)

                if not extraction:
                    warnings.warn(
                        f"No extraction result for part '{key}' in '{item['title']}'"
                    )
                    continue

                encoded_data: List[Dict[str, Any]] = []
                for page in extraction.get('pages', []):
                    for line_no, content in page.get('lines', []):
                        try:
                            encoded = encoder.encode(content)
                            # print(f"content {content }, encoded {encoded}")
                            encoded_data.append({
                                'page': page.get('page_number'),
                                'line': line_no,
                                'original': content,
                                'encoded': encoded,
                            })
                            if verbose:
                                print(
                                    f"    [{key}] Page {page.get('page_number')} "
                                    f"| Line {line_no}: {content[:50]}…"
                                )
                        except Exception as e:
                            warnings.warn(
                                f"Failed to encode line {line_no} of part '{key}' "
                                f"in '{item['title']}': {e}"
                            )

                parts[key] = encoded_data

                if verbose:
                    print(f"  ✓ Encoded {len(encoded_data)} lines for part '{key}'")

            result['parts'] = parts

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