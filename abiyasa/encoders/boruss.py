from .base import BaseEncoder
from typing import Dict, List
class BORUSSEncoder(BaseEncoder):
    BALUNGAN_SYSTEM = {
        'C': '3a', 'D': '4a', 'E': '5a', 'F': '6a', 'G': '7a',
        'H': '1', 'I': '2', 'J': '3', 'K': '4', 'L': '5',
        'M': '6', 'N': '7', 'O': '1b', 'P': '2b', 'Q': '3b',
        'R': '4b', 'S': '5b', 'T': '6b', '-': '0'
    }

    KEPATIHAN_SYSTEM = {
        'e': '3a', 't': '5a', 'y': '6a', 'u': '7a',
        '1': '1', '2': '2', '3': '3', '4': '4', '5': '5',
        '6': '6', '7': '7', '!': '1b', '@': '2b', '#': '3b',
        '%': '5b', '^': '6b', '.': '0'
    }
    def encode(self, sequence: str) -> str:
        elements = self._parse_notation_sequence(sequence)
        notes_to_output = self._extract_notes(elements)
        return notes_to_output

    def decode(self, encoded: str) -> str:
        pass

    def _parse_notation_sequence(self, sequence: str) -> List[Dict]:
        """
        Parse the notation sequence into individual elements.

        Args:
            sequence: The input sequence notation string

        Returns:
            List of dictionaries with 'type' and 'char' keys
        """
        elements = []
        for char in sequence:
            if char in ['Î', 'Ë', 'Ï', 'Õ', '«']:
                elements.append({'type': 'legato_start', 'char': char})
            elif char in ['®', '¬']:
                elements.append({'type': 'legato_end', 'char': char})
            elif self._is_rest_char(char):
                elements.append({'type': 'rest', 'char': char})
            elif char == '_':
                elements.append({'type': 'underscore', 'char': char})
            elif char == ' ':
                elements.append({'type': 'space', 'char': char})
            elif char == 'g':
                elements.append({'type': 'gong', 'char': char})
            elif char == '[':
                elements.append({'type': 'loop_start', 'char': char})
            elif char == ']':
                elements.append({'type': 'loop_end', 'char': char})
            elif self._is_note_char(char):
                elements.append({'type': 'note', 'char': char})
            else:
                if char.isalnum():
                    elements.append({'type': 'note', 'char': char})
                else:
                    elements.append({'type': 'unknown', 'char': char})

        return elements

    def _extract_notes(self, elements: List[Dict]) -> List[Dict]:
        """
        Extract notes and their values from parsed elements.

        Args:
            elements: Parsed notation elements

        Returns:
            List of note dictionaries with GSPN components
        """
        notes_to_output = []
        i = 0

        while i < len(elements):
            elem = elements[i]

            # Skip non-output elements
            if elem['type'] in ['legato_start', 'legato_end', 'space']:
                i += 1
                continue

            # Handle rest
            if elem['type'] == 'rest':
                note_value = ''
                # Check for -_ or ._ pattern
                if i + 1 < len(elements) and elements[i + 1]['type'] == 'underscore':
                    note_value = 'A'

                notes_to_output.append({
                    'note_num': '0',
                    'octave': '',
                    'value': note_value,
                    'original_index': i
                })
                i += 1
                continue

            # Handle _X_ pattern
            if elem['type'] == 'underscore':
                if (i + 2 < len(elements) and
                        elements[i + 1]['type'] == 'note' and
                        elements[i + 2]['type'] == 'underscore'):
                    note_char = elements[i + 1]['char']


                    notes_to_output.append({

                        'value': 'A',
                        'original_index': i
                    })
                    i += 3
                    continue
                else:
                    i += 1
                    continue

            # Handle regular note
            if elem['type'] == 'note':
                note_char = elem['char']

                # note_num, octave = self._get_note_gspn(note_char)
                note_value = ''

                # Check if followed by underscore (X_ pattern)
                if i + 1 < len(elements) and elements[i + 1]['type'] == 'underscore':
                    note_value = 'A'

                notes_to_output.append({
                    # 'note_num': note_num,
                    # 'octave': octave,
                    'value': note_value,
                    'original_index': i
                })
                i += 1
                continue

            i += 1

        return notes_to_output
    @property
    def name(self) -> str:
        return "BORUSS"

    def _is_rest_char(self, char: str) -> bool:
        """Return ``True`` if *char* represents a rest (``'-'`` or ``'.'``)."""
        return char in ['-', '.']
    def _is_note_char(self, char: str) -> bool:
        """Return ``True`` if *char* is a recognised note in the active system."""
        note_map = (self.BALUNGAN_SYSTEM if self.notation_system == 'balungan'
                    else self.KEPATIHAN_SYSTEM)
        return char in note_map
