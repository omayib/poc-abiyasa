"""
OVENS (Odd-even Note Encoder with Structural tags) Encoder

This module encodes a gamelan note sequence using an LSTM-based knowledge
representation scheme with structural tags for bar, line, and phrase position.

Encoding Rules:
- 4 notes per bar, 2 bars per line
- Tags: a (even note), b (even bar), c (even line),
        d (intro), e (body), f (outro)
- '#' prefix on the first token, '*' suffix on the last token
- Tokens are comma-separated
"""

import math
from typing import List, Tuple, Union
from .base import BaseEncoder


class OVENSEncoder(BaseEncoder):
    """
    OVENS (Odd-even Note Encoder with Structural tags) encoder for gamelan music.

    Encodes a sequence of note values with structural position tags
    derived from bar, line, and melodic-phrase boundaries, as used
    in LSTM-based gamelan music modelling.

    Supports both Balungan and Kepatihan notation systems for resolving
    note characters to their pitch number and octave via :meth:`_get_note_ovens`.

    Parameters
    ----------
    notation_system : str
        Either ``'balungan'`` or ``'kepatihan'``.
    """

    # Note mappings from both notation systems
    BALUNGAN_SYSTEM = {
        'C': '3a', 'D': '4a', 'E': '5a', 'F': '6a', 'G': '7a',
        'H': '1',  'I': '2',  'J': '3',  'K': '4',  'L': '5',
        'M': '6',  'N': '7',  'O': '1b', 'P': '2b', 'Q': '3b',
        'R': '4b', 'S': '5b', 'T': '6b', '-': '0'
    }

    KEPATIHAN_SYSTEM = {
        'e': '3a', 't': '5a', 'y': '6a', 'u': '7a',
        '1': '1',  '2': '2',  '3': '3',  '4': '4',  '5': '5',
        '6': '6',  '7': '7',  '!': '1b', '@': '2b', '#': '3b',
        '%': '5b', '^': '6b', '.': '0'
    }

    @property
    def name(self) -> str:
        return "OVENS"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def encode(self, sequence: Union[str, List[int]]) -> str:
        """
        Encode a note sequence to the OVENS tag format.

        Accepts either a list of integer note values **or** a
        space/comma-separated string of integers so the encoder is
        usable from both programmatic and text-pipeline contexts.

        Parameters
        ----------
        sequence : list[int] | str
            Note values (0–7 for gamelan pitch numbers, 0 = rest).

        Returns
        -------
        str
            Comma-separated tagged tokens, e.g.
            ``"#6d,5ad,3bd,2abd,5e,…,3abf*"``

        Examples
        --------
        >>> enc = OVENSEncoder('balungan')
        >>> enc.encode([6, 5, 3, 2])
        '#6d,5ad,3bd,2abd*'
        """
        notes = self._coerce_to_int_list(sequence)
        if not notes:
            return ""

        encoded_tokens = self._build_tokens(notes)
        return ",".join(encoded_tokens)

    def decode(self, encoded: str) -> str:
        """
        Decode an OVENS string back to a space-separated note sequence.

        Strips all tag characters (a–f), the boundary markers ``#`` / ``*``,
        and the comma separators, returning only the raw note values.

        Parameters
        ----------
        encoded : str
            A string previously produced by :meth:`encode`.

        Returns
        -------
        str
            Space-separated note values, e.g. ``"6 5 3 2"``.

        Examples
        --------
        >>> enc = OVENSEncoder('balungan')
        >>> enc.decode('#6d,5ad,3bd,2abd*')
        '6 5 3 2'
        """
        tokens = encoded.split(",")
        note_values = []
        for token in tokens:
            # Remove boundary markers and tag characters
            cleaned = token.lstrip("#").rstrip("*")
            # Tags are lowercase letters a-f; note values are digits
            note_str = "".join(ch for ch in cleaned if ch.isdigit())
            if note_str:
                note_values.append(note_str)
        return " ".join(note_values)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_note_ovens(self, note_char: str) -> Tuple[str, str]:
        """
        Get the pitch number and octave for a note character.

        Mirrors :meth:`GSPNEncoder._get_note_gspn` but looks up values
        from :attr:`BALUNGAN_SYSTEM` or :attr:`KEPATIHAN_SYSTEM` depending
        on the active ``notation_system``.

        Parameters
        ----------
        note_char : str
            A single note character from the input notation.

        Returns
        -------
        tuple[str, str]
            ``(note_number, octave)`` where *octave* is ``''`` (middle),
            ``'a'`` (low), or ``'b'`` (high).
            Returns ``('0', '')`` for unknown characters.

        Examples
        --------
        >>> enc = OVENSEncoder('balungan')
        >>> enc._get_note_ovens('C')
        ('3', 'a')
        >>> enc._get_note_ovens('H')
        ('1', '')
        >>> enc._get_note_ovens('O')
        ('1', 'b')
        """
        note_map = (self.BALUNGAN_SYSTEM if self.notation_system == 'balungan'
                    else self.KEPATIHAN_SYSTEM)
        ovens = note_map.get(note_char, '0')

        if len(ovens) == 1:
            return (ovens, '')
        elif len(ovens) == 2:
            return (ovens[0], ovens[1])
        else:
            return ('0', '')

    def _is_note_char(self, char: str) -> bool:
        """Return ``True`` if *char* is a recognised note in the active system."""
        note_map = (self.BALUNGAN_SYSTEM if self.notation_system == 'balungan'
                    else self.KEPATIHAN_SYSTEM)
        return char in note_map

    def _is_rest_char(self, char: str) -> bool:
        """Return ``True`` if *char* represents a rest (``'-'`` or ``'.'``)."""
        return char in ['-', '.']

    def _coerce_to_int_list(self, sequence: Union[str, List[int]]) -> List[int]:
        """Convert *sequence* to a plain ``list[int]``."""
        if isinstance(sequence, str):
            # Accept space- or comma-separated integer strings
            parts = sequence.replace(",", " ").split()
            return [int(p) for p in parts if p.lstrip("-").isdigit()]
        return [int(n) for n in sequence]

    def _build_tokens(self, notes: List[int]) -> List[str]:
        """
        Build the list of tagged token strings for *notes*.

        Each token has the form ``<note_value><tags>`` where *tags* is a
        (possibly empty) string drawn from ``{a, b, c, d, e, f}``.
        The first token is prefixed with ``'#'`` and the last suffixed
        with ``'*'``.
        """
        np_ = len(notes)

        # Melodic-phrase boundary indices (intro / body / outro)
        c1_limit = math.ceil(np_ * 0.2)        # end of intro   (exclusive)
        c3_limit = math.ceil(np_ * 0.2)        # length of outro
        # c2 occupies the remainder automatically

        tokens: List[str] = []

        for i, note_val in enumerate(notes):
            tags = ""

            # --- Structural position tags ---

            # 'a': even-indexed note within its bar (1-based position)
            if (i + 1) % 2 == 0:
                tags += "a"

            # 'b': note falls in an even-numbered bar (1-based bar index)
            bar_index = (i // 4) + 1
            if bar_index % 2 == 0:
                tags += "b"

            # 'c': note falls in an even-numbered line (1-based line index)
            line_index = (i // 8) + 1
            if line_index % 2 == 0:
                tags += "c"

            # --- Melodic phrase tags ---
            if i < c1_limit:
                tags += "d"                     # intro
            elif i < (np_ - c3_limit):
                tags += "e"                     # body
            else:
                tags += "f"                     # outro

            tokens.append(f"{note_val}{tags}")

        # Boundary markers
        tokens[0] = "#" + tokens[0]
        tokens[-1] = tokens[-1] + "*"

        return tokens