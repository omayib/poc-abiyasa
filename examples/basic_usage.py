"""
Basic usage examples for the Abiyasa package.

This file demonstrates common use cases for loading and processing
Gamelan music datasets.
"""
import json

import abiyasa


def example_basic_usage():
    """Most basic usage - load data with defaults."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Load first 3 items with GSPN encoding
    data = abiyasa.load_data(encoder='GSPN', limit=100, verbose=True, filter_dset ="35_GERONGAN_SM_DSET")
    
    print(f"\nLoaded {len(data)} items")
    
    # Print first item
    if data:
        item = data[0]
        print(f"\nFirst item: {item['title']}")
        print(f"PDF path: {item['pdf_path']}")
        

def example_with_kepatihan():
    """Load data using Kepatihan notation system."""
    print("\n" + "=" * 60)
    print("Example 2: Using Kepatihan Notation")
    print("=" * 60)
    
    data = abiyasa.load_data(
        encoder='GSPN',
        notation_system='kepatihan',
        limit=100,
        verbose=True
    )
    
    for item in data:
        print(f"\nTitle: {item['title']}")
        if 'font_type' in item:
            print(f"Font type: {item['font_type']}")


def example_metadata_only():
    """Load metadata without extracting PDFs."""
    print("\n" + "=" * 60)
    print("Example 3: Metadata Only (No PDF Extraction)")
    print("=" * 60)
    
    # Fast loading - just metadata, no PDF extraction
    metadata = abiyasa.load_data(
        extract_pdf=False,
        limit=5,
        verbose=True
    )
    
    print("\nMetadata loaded:")
    for item in metadata:
        print(f"  - {item['title']} ({item['filename']})")


def example_process_encoded_data():
    """Process and analyze encoded data."""

    print("\n" + "=" * 60)
    print("Example 4: Processing Encoded Data")
    print("=" * 60)
    
    data = abiyasa.load_data(encoder='GSPN', limit=3, verbose=True, filter_dset="35_GERONGAN_SM_DSET")
    
    for item in data:
        print(f"\n{'='*50}")
        print(f"title: {item.get('title', '')}")
        encoded_sequence = item.get('metadata', {}).get('dataset_entry', {}).get('encoded_sequence', '')
        print(f"encoded_sequence: {encoded_sequence}")
        encoded_combined=""
        if 'parts' in item and 'lines' in item['parts']:
            encoded_combined = "".join([line['encoded'] for line in item['parts']['lines']])
            print(f"  Encoded:  {encoded_combined}")
            for line_data in item['parts']['lines']:
                print(f"\n  Page {line_data['page']} | Line {line_data['line']}")
                print(f"  Encoded:  {line_data['encoded']}")
            # 4. Now it's safe to compare
        # if encoded_combined:
        #     compare(reference_gspn, encoded_combined)
        # else:
        #     print("⚠️ No encoded data found to compare.")


def compare(original, encoded):
    diff_marker = ""
    mismatches = []

    # Use zip to compare character by character
    for i, (char_title, char_enc) in enumerate(zip(original, encoded)):
        if char_title == char_enc:
            diff_marker += " "  # Match
        else:
            diff_marker += "^"  # Difference marker
            mismatches.append(f"Pos {i}: Title='{char_title}', Encoded='{char_enc}'")

    # 4. Display results
    # print(f"Encoded: {original[:100]}...")
    # print(f"Encoded: {encoded[:100]}...")
    # print(f"Diff:    {diff_marker[:100]}...")

    if not mismatches:
        print("\n✅ Perfect match!")
    else:
        print(f"\n❌ Found {len(mismatches)} differences.")
        # Show first few specific errors
        for m in mismatches[:5]:
            print(f"  - {m}")

def example_dataset_class():
    """Use GamelanDataset class directly for more control."""
    print("\n" + "=" * 60)
    print("Example 5: Using GamelanDataset Class")
    print("=" * 60)
    
    # Create dataset with custom cache directory
    dataset = abiyasa.GamelanDataset(cache_dir='./my_gamelan_cache')
    
    # Get statistics
    stats = dataset.get_statistics()
    print(f"\nDataset Statistics:")
    print(f"  Total items: {stats['total_items']}")
    print(f"  Cache directory: {stats['cache_directory']}")
    print(f"  Cached PDFs: {stats['cached_pdfs']}")
    print(f"  Available encoders: {', '.join(stats['available_encoders'])}")
    
    # Load data
    data = dataset.load_data(encoder='GSPN', limit=2, verbose=False)
    print(f"\nLoaded {len(data)} items using custom cache directory")


def example_encoder_directly():
    """Use encoder directly without loading dataset."""
    print("\n" + "=" * 60)
    print("Example 6: Using Encoder Directly")
    print("=" * 60)
    
    from abiyasa import GSPNEncoder
    
    # Create encoder for Balungan notation
    encoder = GSPNEncoder(notation_system='balungan')
    
    print(f"Encoder: {encoder.name}")
    print(f"Notation system: {encoder.notation_system}")
    
    # Encode some sequences
    test_sequences = [
        "- - - -",
        "F F",
        "H I J",
        "-_ _F_",
        "ÎI J",
    ]
    
    print("\nEncoding examples:")
    for seq in test_sequences:
        encoded = encoder.encode(seq)
        print(f"  '{seq}' → '{encoded}'")


def example_dataset_info():
    """Get information about the dataset."""
    print("\n" + "=" * 60)
    print("Example 7: Dataset Information")
    print("=" * 60)
    
    info = abiyasa.get_dataset_info()
    
    print("Dataset Information:")
    for key, value in info.items():
        print(f"  {key}: {value}")

def example_qap_encoding():
    """Load and inspect QAP-encoded gamelan skeletal melodies.

    Uses the numeric_seq path — no PDF download or extraction needed.
    Returns a dict with 'compositions', 'QAP_DSET', and 'meta' keys.
    """
    print("\n" + "=" * 60)
    print("Example QAP: QAP Encoding (Fanani et al. 2024)")
    print("=" * 60)

    # ── Load one composition ──────────────────────────────────────────
    data = abiyasa.load_data(
        encoder='QAP',
        limit=1,
        verbose=True
    )

    print(f"\nReturn type : {type(data).__name__}")
    print(f"Top-level keys : {list(data.keys())}")
    print(f"Total loaded   : {data['meta']['total_loaded']}")

    # ── Inspect the single composition ───────────────────────────────
    comp = data['compositions'][0]
    print(f"\n{'─'*50}")
    print(f"Title      : {comp['title']}")
    print(f"Identifier : {comp['metadata']['identifier']}")
    print(f"Lines used : {comp['metadata'].get('dataset_entry', {}).get('lines', '')}")

    qap = comp['qap']
    s   = qap['structure']
    print(f"\nStructure  : beats={s['I']}, pairs={s['II']}, "
          f"bars={s['III']}, lines={s['IV']}")
    print(f"\nBeats  (T) : {qap['beats']}")
    print(f"Pairs  (P) : {qap['pairs']}")
    print(f"X1 (Q)     : {qap['X1']}")
    print(f"X2 (A)     : {qap['X2']}")
    print(f"X3         : {qap['X3']}")
    print(f"X4         : {qap['X4']}")
    print(f"X5         : {qap['X5']}")
    print(f"X6         : begin={qap['X6']['begin']}, end={qap['X6']['end']}")
    print(f"Bars   (B) : {qap['bars']}")
    print(f"Lines  (L) : {qap['lines']}")

    # ── GA gene pool (limit=1 so only pairs from this composition) ───
    print(f"\nQAP_DSET   : {data['QAP_DSET']}")
    print(f"  → {len(data['QAP_DSET'])} unique pair elements "
          f"(full dataset gives 22)")

    # ── Load full dataset and verify the 22-pair gene pool ───────────
    print(f"\n{'─'*50}")
    print("Loading full dataset (all 6 compositions) …")
    full = abiyasa.load_data(
        encoder='QAP',
        verbose=False,
        filter_dset='QAP_DSET'
    )
    n = len(full['QAP_DSET'])
    status = "✓" if n == 22 else "✗"
    print(f"QAP_DSET ({n} unique pairs) {status} : {full['QAP_DSET']}")
    print(f"\nAll {full['meta']['total_loaded']} compositions loaded.")
    for c in full['compositions']:
        s = c['qap']['structure']
        print(f"  [{c['title']}]  beats={s['I']}, pairs={s['II']}, "
              f"bars={s['III']}, lines={s['IV']}")

def main():
    """Run all examples."""
    print("ABIYASA PACKAGE - USAGE EXAMPLES")
    print("=" * 60)
    
    try:
        #example_basic_usage()
        # example_with_kepatihan()
        # example_metadata_only()
        # example_process_encoded_data()

        example_qap_encoding()
        # example_dataset_class()
        #example_encoder_directly()
        # example_dataset_info()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
