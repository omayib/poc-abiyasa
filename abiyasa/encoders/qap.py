"""
QAP (Question-Answer Phrase) Encoder

Implements the full QAP encoding pipeline for Gamelan skeletal melody as described in:

    Fanani, A. Z., Syarif, A. M., Shidik, G. F., & Marjuni, A. (2024).
    "Expressing and Developing Melodic Phrases in Gamelan Skeletal Melody
    Generation Using Genetic Algorithm."
    IEEE Access. DOI: 10.1109/ACCESS.2024.3457880

Pipeline:
    Stage 1 — Dotted note encoding   : dotted notes (·) stored/coded as 9
    Stage 2 — Beat-to-pair mapping   : Pk = T[k*2]*10 + T[k*2+1]
    Stage 3 — QAP feature extraction : X1, X2, X3, X4, X5, X6
    Stage 4 — GA gene pool           : unique sorted pairs → QAP_DSET
"""

from typing import Dict, List, Any, Optional
from .base import BaseEncoder

# Dotted notes are coded as this integer during encoding
DOTTED_NOTE_CODE = 9


class QAPEncoder(BaseEncoder):
    """
    QAP (Question-Answer Phrase) encoder for Gamelan skeletal melody.

    Like GSPNEncoder, accepts raw notation strings from either the Balungan
    or Kepatihan system and maps them to integer beat values before running
    the QAP pipeline.  The notation_system parameter controls which map is
    used (default: 'balungan').

    Note maps (character → integer beat):
        BALUNGAN_SYSTEM  — uppercase letter notation  (H=1, I=2, J=3 …)
        KEPATIHAN_SYSTEM — numeric/symbol notation    (1=1, 2=2, 3=3 …)

    The encoder exposes two levels of API:

    1. ``encode(sequence)``        — BaseEncoder interface: notation string in,
                                     space-separated QAP pair string out.

    2. ``encode_sequence(beats)``  — primary API: integer beat list in, full
                                     dict out (pairs, X1–X6, bars, lines,
                                     structure).

    3. ``encode_dataset(comps)``   — aggregate multiple compositions and
                                     compute the combined GA gene pool
                                     (``QAP_DSET``).
    """

    # ── Note maps (character → integer beat) ─────────────────────────────────
    # Octave markers from GSPN (a=low, b=high) are stripped — QAP works on
    # pitch class integers only (1–7), matching the paper's numeric_seq format.

    BALUNGAN_SYSTEM: Dict[str, str] = {
        'C': '3', 'D': '4', 'E': '5', 'F': '6', 'G': '7',
        'H': '1', 'I': '2', 'J': '3', 'K': '4', 'L': '5',
        'M': '6', 'N': '7', 'O': '1', 'P': '2', 'Q': '3',
        'R': '4', 'S': '5', 'T': '6', '-': '0',
    }

    KEPATIHAN_SYSTEM: Dict[str, str] = {
        'e': '3', 't': '5', 'y': '6', 'u': '7',
        '1': '1', '2': '2', '3': '3', '4': '4', '5': '5',
        '6': '6', '7': '7', '!': '1', '@': '2', '#': '3',
        '%': '5', '^': '6', '.': '0',
    }

    @property
    def name(self) -> str:
        return "QAP"

    # ── Note-character helpers (mirrors GSPNEncoder pattern) ─────────────────

    def _get_note_int(self, char: str) -> Optional[int]:
        """
        Map a notation character to its integer beat value.

        Uses BALUNGAN_SYSTEM or KEPATIHAN_SYSTEM depending on
        ``self.notation_system``.  Returns None for unknown characters
        (spaces, legato markers, etc.) so callers can skip them.

        Args:
            char: Single notation character.

        Returns:
            Integer beat value (0–7), or None if not a note character.
        """
        note_map = (
            self.BALUNGAN_SYSTEM
            if self.notation_system == 'balungan'
            else self.KEPATIHAN_SYSTEM
        )
        val = note_map.get(char)
        return int(val) if val is not None else None

    def _notation_to_beats(self, sequence: str) -> List[int]:
        """
        Convert a raw notation string to an integer beat list.

        Non-note characters (spaces, legato markers, underscores, etc.) are
        silently skipped — only mapped note characters are included.

        Args:
            sequence: Raw notation string, e.g. "H I J K" or "1 2 3 4"
                      or "- - - - O O" (Balungan), or "2 3 2 3" (Kepatihan).

        Returns:
            List of integer beat values, e.g. [1, 2, 3, 4].
        """
        beats = []
        for char in sequence:
            val = self._get_note_int(char)
            if val is not None:
                beats.append(val)
        return beats

    # ── BaseEncoder interface (string in / string out) ────────────────────────

    def encode(self, sequence: str) -> str:
        """
        Encode a notation string into a space-separated QAP pair string.

        Accepts the same notation formats as GSPNEncoder:
            Balungan  : "H I J K L M"  or  "- - - - O O"
            Kepatihan : "1 2 3 4 5 6"  or  ". . 1 2"

        For richer output (X1–X6, bars, lines, structure) use
        ``encode_sequence`` with a pre-built integer beat list.

        Args:
            sequence: Raw notation string (Balungan or Kepatihan).

        Returns:
            Space-separated QAP pair integers, e.g. "12 34 56"
        """
        beats = self._notation_to_beats(sequence)
        result = self.encode_sequence(beats)
        return ' '.join(str(p) for p in result['pairs'])

    def decode(self, encoded: str) -> str:
        """
        Decode a space-separated QAP pair string back to integer beat values.

        Note: decoded values are pitch-class integers (0–7), not the original
        notation characters, because the note-map is not reversible (multiple
        notation characters map to the same integer).

        Args:
            encoded: Space-separated QAP pair integers, e.g. "23 23 12 32"

        Returns:
            Space-separated beat integers, e.g. "2 3 2 3 1 2"
        """
        pairs = [int(x) for x in encoded.strip().split()]
        beats = self._decode_pairs(pairs)
        return ' '.join(str(b) for b in beats)

    # ── Primary API ───────────────────────────────────────────────────────────

    def encode_sequence(self, beats: List[int]) -> Dict[str, Any]:
        """
        Apply the full QAP pipeline to a single composition's beat sequence.

        Args:
            beats: List of integer note values (dotted notes already coded as 9)

        Returns:
            Dict with keys:
                beats     : list[int]  — Stage 1 encoded beat sequence
                pairs     : list[int]  — Stage 2 pair elements (tens values)
                X1        : list[int]  — even-order pairs (questions)
                X2        : list[int]  — odd-order pairs  (answers)
                X3        : list[int]  — beat-level correlation X1 ↔ X2
                X4        : list[int]  — bar-level correlation
                X5        : list[int]  — line-level correlation
                X6        : dict       — {"begin": int, "end": int}
                bars      : list[int]  — bar elements (thousands values)
                lines     : list[int]  — melodic line elements (10M values)
                structure : dict       — {"I": beats, "II": pairs,
                                          "III": bars, "IV": lines}
        """
        # Stage 1: dotted notes are already coded as 9 in the dataset
        encoded_beats = list(beats)

        # Stage 2: beat-to-pair mapping
        pairs = self._encode_pairs(encoded_beats)

        # Stage 3: QAP feature extraction
        features = self._extract_features(pairs)

        # Structural metadata
        structure = self._compute_structure(encoded_beats)

        return {
            'beats':     encoded_beats,
            'pairs':     pairs,
            'X1':        features['X1'],
            'X2':        features['X2'],
            'X3':        features['X3'],
            'X4':        features['X4'],
            'X5':        features['X5'],
            'X6':        features['X6'],
            'bars':      features['bars'],
            'lines':     features['lines'],
            'structure': structure,
        }

    def encode_dataset(self, compositions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Encode multiple compositions and compute the combined GA gene pool.

        Each entry in ``compositions`` must contain an ``'encoded'`` key
        produced by ``encode_sequence``, or alternatively a ``'pairs'`` key.

        Args:
            compositions: List of dicts, each with at least a 'pairs' key
                          (i.e. the output of encode_sequence).

        Returns:
            Dict with keys:
                QAP_DSET : list[int] — unique sorted pair elements across all
                                       compositions (the GA gene pool, Stage 4)
        """
        all_pairs = []
        for comp in compositions:
            all_pairs.extend(comp.get('pairs', []))
        qap_dset = sorted(set(all_pairs))
        return {'QAP_DSET': qap_dset}

    # ── Stage 2: beat-to-pair mapping ────────────────────────────────────────

    def _encode_pairs(self, beats: List[int]) -> List[int]:
        """
        Stage 2: Map two consecutive beats → one pair element.

        Formula (from paper eq. 3):
            Pk = (T[k*2] * 10) + T[k*2+1],  k = 0, 1, …, N/2 - 1
        """
        pairs = []
        for k in range(len(beats) // 2):
            pk = (beats[k * 2] * 10) + beats[k * 2 + 1]
            pairs.append(pk)
        return pairs

    def _decode_pairs(self, pairs: List[int]) -> List[int]:
        """Reverse of _encode_pairs: split each tens value back to two beats."""
        beats = []
        for p in pairs:
            beats.append(p // 10)   # first digit  → question beat
            beats.append(p % 10)    # second digit → answer beat
        return beats

    # ── Stage 3: QAP feature extraction ──────────────────────────────────────

    def _extract_features(self, pairs: List[int]) -> Dict[str, Any]:
        """
        Stage 3: Extract all six QAP features from the pair sequence.

        Features:
            X1  even-order pair elements (index 0, 2, 4, …) — questions
            X2  odd-order pair elements  (index 1, 3, 5, …) — answers
            X3  beat-level correlation: (second digit of X1[k]) ×10
                                      + (first digit  of X2[k])
            X4  bar-level correlation:  (last digit of B[k*2])  ×10
                                      + (first digit of B[k*2+1])
                                      (last bar wraps to first)
            X5  line-level correlation: (last digit of L[k*2])  ×10
                                      + (first digit of L[k*2+1])
                                      (last line wraps to first)
            X6  conversation boundary: begin = X1[0], end = X2[-1]
        """
        # X1 / X2
        X1 = [pairs[i] for i in range(0, len(pairs), 2)]
        X2 = [pairs[i] for i in range(1, len(pairs), 2)]

        # X3: second digit of X1[k] × 10  +  first digit of X2[k]
        X3 = []
        for k in range(min(len(X1), len(X2))):
            ak = (X1[k] % 10) * 10       # second digit of X1[k] × 10
            bk = X2[k] // 10             # first digit  of X2[k]
            X3.append(ak + bk)

        # Bars: Bk = X1[k] * 100 + X2[k]  (four-digit thousands value)
        bars: List[int] = []
        for k in range(min(len(X1), len(X2))):
            bars.append(X1[k] * 100 + X2[k])

        # Lines: Lk = B[k*2] * 10000 + B[k*2+1]  (eight-digit value)
        lines: List[int] = []
        for k in range(len(bars) // 2):
            lines.append(bars[k * 2] * 10000 + bars[k * 2 + 1])

        # X4: bar-level correlation
        # For each bar k: (last digit of B[k]) × 10 + (first digit of B[k+1])
        # The last bar wraps around to B[0]
        X4: List[int] = []
        for k in range(len(bars)):
            b_curr = bars[k]
            b_next = bars[(k + 1) % len(bars)]
            ak = (b_curr % 10) * 10
            bk = int(str(b_next)[0])     # first digit of four-digit bar
            X4.append(ak + bk)

        # X5: line-level correlation
        # For each line k: (last digit of L[k]) × 10 + (first digit of L[k+1])
        # The last line wraps around to L[0]
        X5: List[int] = []
        for k in range(len(lines)):
            l_curr = lines[k]
            l_next = lines[(k + 1) % len(lines)]
            ak = (l_curr % 10) * 10
            bk = int(str(l_next)[0])     # first digit of eight-digit line
            X5.append(ak + bk)

        # X6: conversation boundary markers
        X6 = {
            'begin': X1[0]  if X1 else None,
            'end':   X2[-1] if X2 else None,
        }

        return {
            'X1':    X1,
            'X2':    X2,
            'X3':    X3,
            'X4':    X4,
            'X5':    X5,
            'X6':    X6,
            'bars':  bars,
            'lines': lines,
        }

    # ── Structural metadata ───────────────────────────────────────────────────

    def _compute_structure(self, beats: List[int]) -> Dict[str, int]:
        """
        Compute structural element counts.

        Formula (from paper eq. 1):
            I   = N          (total beats)
            II  = N/2        (total pairs)
            III = N/R        (total bars,  R=4)
            IV  = N/(R×2)    (total lines, R=4)
        """
        R = 4  # beats per bar (constant in Gamelan Lancaran)
        N = len(beats)
        return {
            'I':   N,
            'II':  N // 2,
            'III': N // R,
            'IV':  N // (R * 2),
        }