"""
Core dataset loading and management functionality.
"""
from __future__ import annotations

import json
import os
from importlib.metadata import metadata
from pathlib import Path
from typing import List, Dict, Any, Optional
import warnings

from ..encoders import BaseEncoder, GSPNEncoder, QAPEncoder, BORUSSEncoder
from ..encoders.ovens import OVENSEncoder
from ..extractors.font_parser import parse_pdf_font
from ..extractors.line_extractor import extract_kepatihan_from_pdf
from ..utils.downloader import download_gamelan_file

# Pre-computed sequence keys checked per encoder when filter_dset is active.
# If the matching used_by entry contains the key, the loader uses it directly
# and skips PDF download/extraction.  Falls back to PDF if the key is absent.
#
#   GSPN encoder -> looks for 'encoded_sequence'  (ready-made GSPN string)
#   QAP  encoder -> looks for 'numeric_seq'       (integer beat list)
#
# No dataset-name allowlist is needed — the presence of the key in the JSON
# is the only gate, so this works for QAP_DSET, 35_GERONGAN_SM_DSET,
# 59_LADRANG_SM_DSET, and any future dataset that stores pre-computed seqs.
_GSPN_SEQ_KEY = 'encoded_sequence'
_QAP_SEQ_KEY  = 'numeric_seq'
_OVENS_SEQ_KEY  = 'numeric_seq'


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
            'OVENS':OVENSEncoder,
            'BORUSS':BORUSSEncoder
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
    ) -> dict[str, list[Any] | dict[str, str | None | int] | Any] | list[Any]:
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
        is_gspn = isinstance(encoder_instance, GSPNEncoder)
        is_qap  = isinstance(encoder_instance, QAPEncoder)
        is_ovens = isinstance(encoder_instance, OVENSEncoder)
        is_boruss=isinstance(encoder_instance,BORUSSEncoder)

        results = []
        if filter_dset:
            if verbose:
                print(f"[abiyasa] filter_dset='{filter_dset}' active")
            items = [item for item in self.metadata
                     if any(usage.get('dataset_name') == filter_dset
                            for usage in item.get('used_by', []))]
        else:
            items = self.metadata[:limit] if limit else self.metadata

        if limit is not None:
            items = items[:limit]

        total = len(items)
        print(f"item: {total}")

        for idx, item in enumerate(items, 1):
            if verbose:
                print(f"\n[{idx}/{total}] Processing: {item['title']}")

            try:
                # Resolve the active used_by entry for this item (if any)
                dataset_entry = None
                if filter_dset:
                    dataset_entry = next(
                        (u for u in item.get('used_by', [])
                         if u.get('dataset_name') == filter_dset),
                        None
                    )

                # Routing: prefer pre-computed sequences from the JSON when
                # filter_dset is active and the entry carries the right key.
                # Fall back to PDF extraction when the key is absent.
                #
                #   GSPN + encoded_sequence present → _process_item_gspn_from_seq
                #   QAP  + numeric_seq present       → _process_item_qap
                #   anything else                    → _process_item  (PDF path)

                # ── Routing: prefer pre-computed sequences when available ──
                if (is_gspn and filter_dset and dataset_entry is not None
                        and dataset_entry.get(_GSPN_SEQ_KEY)):
                    result = self._process_item_gspn_from_seq(
                        item, encoder_instance, verbose,
                        dataset_name=filter_dset
                    )
                elif (is_qap and filter_dset and dataset_entry is not None
                        and dataset_entry.get(_QAP_SEQ_KEY)):
                    result = self._process_item_qap(
                        item, encoder_instance, verbose,
                        dataset_name=filter_dset
                    )
                elif (is_ovens and filter_dset and dataset_entry is not None
                        and dataset_entry.get(_OVENS_SEQ_KEY)):
                    result = self._process_item_ovens(
                        item, encoder_instance, verbose,
                        dataset_name=filter_dset
                    )
                elif is_qap:
                    result = self._process_item_qap(
                        item, encoder_instance,
                        extract_pdf=extract_pdf,
                        verbose=verbose,
                        dataset_name=None,
                    )
                elif is_ovens:
                    result = self._process_item_ovens(
                        item, encoder_instance, verbose,
                        dataset_name=filter_dset,
                    )
                else:
                    # Default path: GSPN or any other encoder via PDF extraction
                    result = self._process_item(
                        item, encoder_instance, extract_pdf, verbose,
                        dataset_name=filter_dset,
                    )
                results.append(result)
            except Exception as e:
                if verbose:
                    print(f"  ✗ Error processing {item['title']}: {e}")
                warnings.warn(f"Failed to process {item['title']}: {e}")
                continue

        if verbose:
            print(f"\n✓ Successfully loaded {len(results)}/{total} items")
        # For QAP encoder, always return the wrapped dict structure so callers
        # get a consistent shape regardless of whether filter_dset was set.
        if is_qap and any('qap' in r for r in results):
            qap_dset = encoder_instance.encode_dataset(
                [r['qap'] for r in results if 'qap' in r]
            )['QAP_DSET']
            if verbose:
                print(f"  QAP_DSET ({len(qap_dset)} unique pairs): {qap_dset}")
            return {
                'compositions': results,
                'QAP_DSET': qap_dset,
                'meta': {
                    'encoder':      encoder,
                    'filter_dset':  filter_dset,
                    'limit':        limit,
                    'total_loaded': len(results),
                    'reference':    '10.1109/ACCESS.2024.3457880',
                }
            }

        # For OVENS encoder, return a wrapped dict with the flat token sequence
        # concatenated across all compositions alongside the per-item results.
        if is_ovens and any('ovens' in r for r in results):
            all_tokens = []
            for r in results:
                if 'ovens' in r:
                    all_tokens.extend(r['ovens'].split(','))
            ovens_dset = ','.join(all_tokens)
            if verbose:
                print(f"  OVENS_DSET ({len(all_tokens)} tokens total)")
            return {
                'compositions': results,
                'OVENS_DSET': ovens_dset,
                'meta': {
                    'encoder':      encoder,
                    'filter_dset':  filter_dset,
                    'limit':        limit,
                    'total_loaded': len(results),
                }
            }

        return results

    def _process_item_gspn_from_seq(
        self,
        item: Dict[str, Any],
        encoder: 'GSPNEncoder',
        verbose: bool,
        dataset_name: str,
    ) -> Dict[str, Any]:
        """
        Process a single dataset item using GSPN encoding from ``numeric_seq``.

        This path is taken when encoder='GSPN', filter_dset is active, and
        the matching ``used_by`` entry contains an ``encoded_sequence`` key
        (a pre-computed GSPN string).  No PDF download or extraction occurs.

        The ``encoded_sequence`` value is a ready-made GSPN string stored
        directly in the dataset JSON (e.g. for 35_GERONGAN_SM_DSET and
        59_LADRANG_SM_DSET).  It is stored as-is into ``parts['lines']``
        without re-encoding, mirroring the structure that ``_process_item``
        would produce so all downstream code remains uniform.

        Args:
            item:         Dataset item metadata dict.
            encoder:      GSPNEncoder instance (used only for metadata).
            verbose:      Whether to print progress.
            dataset_name: The dataset_name to match in used_by.

        Returns:
            Dict with keys:
                title      : str
                filename   : str
                pdf_path   : str   (empty — no PDF used)
                parts      : {'lines': list[dict]}  one entry per line in the
                             encoded_sequence value.  Each dict has keys:
                                 page     : None
                                 line     : int   (1-indexed)
                                 original : str   (raw encoded_sequence value)
                                 encoded  : str   (same — already GSPN)
                metadata   : dict  (identifier, used_by, dataset_entry)
        """
        # ── 1. Resolve the matching used_by entry ─────────────────────
        dataset_entry = next(
            (u for u in item.get('used_by', [])
             if u.get('dataset_name') == dataset_name),
            None
        )
        if dataset_entry is None:
            raise ValueError(
                f"No 'used_by' entry with dataset_name='{dataset_name}' "
                f"found for item '{item['title']}'"
            )

        encoded_sequence = dataset_entry.get(_GSPN_SEQ_KEY)
        if not encoded_sequence:
            raise ValueError(
                f"'{_GSPN_SEQ_KEY}' is missing or empty in used_by entry "
                f"for '{item['title']}' (dataset_name='{dataset_name}')"
            )

        # ── 2. Store the pre-computed sequence ────────────────────────
        # encoded_sequence may be a plain GSPN string or a list of strings
        # (one per notation line).  Normalise to a list so the output shape
        # is always consistent with what _process_item returns.
        if isinstance(encoded_sequence, list):
            seq_lines = encoded_sequence
        else:
            seq_lines = [encoded_sequence]

        encoded_lines: List[Dict[str, Any]] = []
        for line_idx, seq_str in enumerate(seq_lines, start=1):
            encoded_lines.append({
                'page':     None,
                'line':     line_idx,
                'original': seq_str,
                'encoded':  seq_str,
            })

        if verbose:
            total_chars = sum(len(d['encoded']) for d in encoded_lines)
            print(f"  ✓ GSPN (from {_GSPN_SEQ_KEY}, "
                  f"{len(encoded_lines)} line(s), {total_chars} chars)")

        return {
            'title':    item['title'],
            'filename': item.get('filename', ''),
            'pdf_path': '',
            'parts': {
                'lines': encoded_lines,
            },
            'metadata': {
                'identifier':    item.get('identifier', {}),
                'used_by':       item.get('used_by', []),
                'dataset_entry': dataset_entry,
            },
        }

    def _process_item_qap(
        self,
        item: Dict[str, Any],
        encoder: 'QAPEncoder',
        extract_pdf: bool = True,
        verbose: bool = True,
        dataset_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a single dataset item using the QAP encoder.

        Two paths depending on whether ``dataset_name`` is provided:

        With dataset_name (filter_dset active):
            Reads ``numeric_seq`` directly from the matching ``used_by`` entry
            in the JSON and runs the full QAP pipeline.  No PDF is needed.

        Without dataset_name (no filter_dset):
            Falls through to ``_process_item`` for PDF download + extraction,
            then re-encodes each extracted notation line through the QAP
            encoder (notation string → beats → QAP pipeline) and attaches the
            ``qap`` key to the result.

        Args:
            item:         Dataset item metadata dict.
            encoder:      QAPEncoder instance.
            extract_pdf:  Whether to extract notation from PDF (no-filter path).
            verbose:      Whether to print progress.
            dataset_name: The dataset_name to match in used_by, or None.

        Returns:
            Same structure as ``_process_item``:
                title     : str
                filename  : str
                pdf_path  : str   (empty when dataset_name provided)
                metadata  : dict  (identifier, used_by, dataset_entry)
                parts     : {'lines': list[dict]}
                qap       : dict  — beats, pairs, X1–X6, bars, lines, structure
        """
        # ── Path A: dataset_name provided → read numeric_seq from JSON ────────
        if dataset_name:
            dataset_entry = next(
                (u for u in item.get('used_by', [])
                 if u.get('dataset_name') == dataset_name),
                None
            )
            if dataset_entry is None:
                raise ValueError(
                    f"No 'used_by' entry with dataset_name='{dataset_name}' "
                    f"found for item '{item['title']}'"
                )

            numeric_seq = dataset_entry.get(_QAP_SEQ_KEY)
            if not numeric_seq:
                raise ValueError(
                    f"'{_QAP_SEQ_KEY}' is missing or empty in used_by entry "
                    f"for '{item['title']}' (dataset_name='{dataset_name}')"
                )

            # Run full QAP pipeline on the pre-extracted integer beat list
            qap_result = encoder.encode_sequence(numeric_seq)

            # Build parts['lines'] — one entry per beat, same shape as
            # _process_item's per-line dicts so downstream code is uniform.
            #   original = raw beat integer (str)
            #   encoded  = QAP pair shared by the two beats in that pair (str)
            pairs = qap_result['pairs']
            beats = qap_result['beats']
            lines_out: List[Dict[str, Any]] = []
            for beat_idx, beat_val in enumerate(beats):
                pair_val = pairs[beat_idx // 2] if beat_idx // 2 < len(pairs) else None
                lines_out.append({
                    'page':     None,
                    'line':     beat_idx + 1,
                    'original': str(beat_val),
                    'encoded':  str(pair_val) if pair_val is not None else '',
                })

            source   = dataset_entry if dataset_entry.get('filename') else item
            filename = source.get('filename') or item.get('filename', '')

            result = {
                'title':    item['title'],
                'filename': filename,
                'pdf_path': '',
                'metadata': {
                    'identifier':    item.get('identifier', {}),
                    'used_by':       item.get('used_by', []),
                    'dataset_entry': dataset_entry,
                },
                'parts': {'lines': lines_out},
                'qap':   qap_result,
            }

        # ── Path B: no dataset_name → PDF extraction + QAP re-encode ─────────
        else:
            # Use the standard _process_item to handle PDF download + extraction.
            # This gives us parts['lines'] with 'original' notation strings.
            result = self._process_item(
                item, encoder, extract_pdf, verbose, dataset_name=None
            )

            # Collect all notation lines from every part and encode through QAP.
            # Each 'original' string is a raw notation line from the PDF
            # (Balungan or Kepatihan characters) — QAPEncoder._notation_to_beats
            # maps them to integer beats before running the pipeline.
            all_beats: List[int] = []
            for part_lines in result.get('parts', {}).values():
                for line_dict in part_lines:
                    original = line_dict.get('original', '')
                    beats = encoder._notation_to_beats(original)
                    all_beats.extend(beats)

            if all_beats:
                qap_result = encoder.encode_sequence(all_beats)
                result['qap'] = qap_result
            else:
                warnings.warn(
                    f"No beats extracted from PDF lines for '{item['title']}'; "
                    "'qap' key will be absent from result."
                )

        if verbose and 'qap' in result:
            qap_result = result['qap']
            s = qap_result['structure']
            print(f"  ✓ QAP | beats={s['I']}, pairs={s['II']}, "
                  f"bars={s['III']}, lines={s['IV']}")
            print(f"  pairs : {qap_result['pairs']}")
            print(f"  X1    : {qap_result['X1']}")
            print(f"  X2    : {qap_result['X2']}")
            print(f"  X3    : {qap_result['X3']}")
            print(f"  X4    : {qap_result['X4']}")
            print(f"  X5    : {qap_result['X5']}")
            print(f"  X6    : begin={qap_result['X6']['begin']}, "
                  f"end={qap_result['X6']['end']}")

        return result

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
        print(f'pdf path {pdf_path}')

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
                        print(f"line {line_no}, content: {content}")

                        try:
                            encoded = encoder.encode(content)
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

    def _process_item_ovens(
        self,
        item: Dict[str, Any],
        encoder: 'OVENSEncoder',
        verbose: bool,
        dataset_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a single dataset item using the OVENS encoder.

        Two paths depending on whether ``dataset_name`` is provided:

        With dataset_name (filter_dset active):
            Reads ``numeric_seq`` directly from the matching ``used_by`` entry
            in the JSON and runs :meth:`OVENSEncoder.encode` on the integer
            beat list.  No PDF download or extraction occurs.

        Without dataset_name (no filter_dset):
            Falls through to ``_process_item`` for PDF download + extraction,
            then re-encodes each extracted notation line through the OVENS
            encoder and attaches the ``ovens`` key to the result.

        Args:
            item:         Dataset item metadata dict.
            encoder:      OVENSEncoder instance.
            verbose:      Whether to print progress.
            dataset_name: The dataset_name to match in used_by, or None.

        Returns:
            Dict with keys:
                title    : str
                filename : str
                pdf_path : str   (empty when dataset_name provided)
                metadata : dict  (identifier, used_by, dataset_entry)
                parts    : {'lines': list[dict]}
                ovens    : str   — full OVENS-encoded comma-separated sequence
        """
        # ── Path A: dataset_name provided → read numeric_seq from JSON ─────
        if dataset_name:
            dataset_entry = next(
                (u for u in item.get('used_by', [])
                 if u.get('dataset_name') == dataset_name),
                None
            )
            if dataset_entry is None:
                raise ValueError(
                    f"No 'used_by' entry with dataset_name='{dataset_name}' "
                    f"found for item '{item['title']}'"
                )

            numeric_seq = dataset_entry.get(_OVENS_SEQ_KEY)
            if not numeric_seq:
                raise ValueError(
                    f"'{_OVENS_SEQ_KEY}' is missing or empty in used_by entry "
                    f"for '{item['title']}' (dataset_name='{dataset_name}')"
                )

            # Normalise numeric_seq to a plain list of ints.
            # In the JSON it is always a list, but guard against a
            # comma-separated string just in case.
            if isinstance(numeric_seq, str):
                note_list = [int(n) for n in numeric_seq.split(',') if n.strip()]
            else:
                note_list = [int(n) for n in numeric_seq]

            # Encode the whole sequence at once, then split back into
            # individual tokens — one token per note in note_list.
            ovens_encoded = encoder.encode(note_list)
            tokens = ovens_encoded.split(',')

            # Build parts['lines'] by zipping note_list with tokens so each
            # entry corresponds to exactly one note value, not one CSV chunk.
            lines_out: List[Dict[str, Any]] = []
            for note_idx, (note_val, token) in enumerate(zip(note_list, tokens)):
                lines_out.append({
                    'page':     None,
                    'line':     note_idx + 1,
                    'original': str(note_val),
                    'encoded':  token,
                })

            source   = dataset_entry if dataset_entry.get('filename') else item
            filename = source.get('filename') or item.get('filename', '')

            if verbose:
                print(f"  ✓ OVENS | {len(tokens)} tokens from '{_OVENS_SEQ_KEY}'")

            return {
                'title':    item['title'],
                'filename': filename,
                'pdf_path': '',
                'metadata': {
                    'identifier':    item.get('identifier', {}),
                    'used_by':       item.get('used_by', []),
                    'dataset_entry': dataset_entry,
                },
                'parts': {'lines': lines_out},
                'ovens': ovens_encoded,
            }

        # ── Path B: no dataset_name → PDF extraction + OVENS re-encode ─────
        result = self._process_item(
            item, encoder, extract_pdf=True, verbose=verbose,
            dataset_name=None
        )

        # `_process_item` stores raw notation strings (Balungan/Kepatihan
        # characters such as "H I J K L") in each line_dict['original'].
        # These are NOT integers — we must map each character to its pitch
        # number using _get_note_ovens, which consults the active notation
        # system's MAP (BALUNGAN_SYSTEM / KEPATIHAN_SYSTEM) and returns a
        # (note_num_str, octave_str) tuple.  We collect only the note_num
        # part as an int, skipping spaces and unknown chars (0 = rest for '-'
        # and '.', which are already handled by the map).
        all_notes: List[int] = []
        for part_lines in result.get('parts', {}).values():
            for line_dict in part_lines:
                original = line_dict.get('original', '')
                for char in original:
                    if char == ' ':
                        continue
                    if encoder._is_note_char(char):
                        note_num_str, _ = encoder._get_note_ovens(char)
                        try:
                            all_notes.append(int(note_num_str))
                        except ValueError:
                            pass
                    elif encoder._is_rest_char(char):
                        # Rest characters ('-' / '.') map to 0
                        all_notes.append(0)
                    # Unknown chars (gong markers, brackets, etc.) are skipped

        if all_notes:
            ovens_encoded = encoder.encode(all_notes)
            tokens = ovens_encoded.split(',')

            # Re-annotate each line_dict with per-note encoded tokens so
            # parts['lines'] has one entry per note, consistent with Path A.
            flat_lines: List[Dict[str, Any]] = []
            for note_idx, (note_val, token) in enumerate(zip(all_notes, tokens)):
                flat_lines.append({
                    'page':     None,
                    'line':     note_idx + 1,
                    'original': str(note_val),
                    'encoded':  token,
                })
            result['parts']['lines'] = flat_lines
            result['ovens'] = ovens_encoded

            if verbose:
                print(f"  ✓ OVENS | {len(tokens)} tokens (PDF path)")
        else:
            warnings.warn(
                f"No notes extracted from PDF lines for '{item['title']}'; "
                "'ovens' key will be absent from result."
            )

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