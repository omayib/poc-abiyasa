"""
GSPN (Gendhing Scientific Pitch Notation) Encoder

This module converts gamelan music sequence notation to GSPN format as described in:
Syarif, A. M., Azhari, A., Suprapto, S., & Hastuti, K. (2020).
"Human and computation-based musical representation for Gamelan music."
Malaysian Journal of Music, 9, 82-100.

GSPN Format: T + W + V + G
- T: Note number (0-7, where 0 is rest)
- W: Octave/register (empty=middle, a=low, b=high)
- V: Note value (empty=1, A=1/2, B=1/4)
- G: Legato (empty=none, x=start, y=end)
"""

from typing import Dict, List
from .base import BaseEncoder


class GSPNEncoder(BaseEncoder):
    """
    GSPN (Gendhing Scientific Pitch Notation) encoder for gamelan music.
    
    Supports both Balungan and Kepatihan notation systems.
    """
    
    # Note mappings from both notation systems
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
    
    @property
    def name(self) -> str:
        return "GSPN"
    
    def encode(self, sequence: str) -> str:
        """
        Convert sequence notation to GSPN format.
        
        Args:
            sequence: Input sequence notation string
            
        Returns:
            GSPN format string
            
        Examples:
            >>> encoder = GSPNEncoder('balungan')
            >>> encoder.encode("- - - - F F")
            '00006a6a'
            >>> encoder.encode("-_ _F_")
            '0A6aA'
            >>> encoder.encode("ÎI J")
            '2x3y'
        """
        elements = self._parse_notation_sequence(sequence)
        notes_to_output = self._extract_notes(elements)
        self._apply_legato_markers(elements, notes_to_output)
        
        # Build final GSPN string
        result = []
        for note in notes_to_output:
            gspn = note['note_num'] + note['octave'] + note['value'] + note.get('legato', '')
            result.append(gspn)
        
        return ''.join(result)
    
    def decode(self, encoded: str) -> str:
        """
        Decode GSPN format back to notation sequence.
        
        Note: This is a simplified decoder and may not perfectly reconstruct
        the original notation with all legato markers.
        
        Args:
            encoded: GSPN encoded string
            
        Returns:
            Approximate notation sequence string
        """
        # This is a placeholder implementation
        # Full implementation would require parsing GSPN tokens
        raise NotImplementedError("GSPN decoding is not yet implemented")
    
    def _get_note_gspn(self, note_char: str) -> tuple:
        """
        Get the GSPN representation for a note character.
        
        Args:
            note_char: The note character from input notation
            
        Returns:
            Tuple of (note_number, octave) e.g., ('3', 'a') or ('1', '')
        """
        note_map = (self.BALUNGAN_SYSTEM if self.notation_system == 'balungan' 
                   else self.KEPATIHAN_SYSTEM)
        gspn = note_map.get(note_char, '0')
        
        # Parse the GSPN string to extract note number and octave
        if len(gspn) == 1:
            return (gspn, '')
        elif len(gspn) == 2:
            return (gspn[0], gspn[1])
        else:
            return ('0', '')
    
    def _is_note_char(self, char: str) -> bool:
        """Check if a character represents a note."""
        note_map = (self.BALUNGAN_SYSTEM if self.notation_system == 'balungan' 
                   else self.KEPATIHAN_SYSTEM)
        return char in note_map
    
    def _is_rest_char(self, char: str) -> bool:
        """Check if a character represents a rest."""
        return char in ['-', '.']
    
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
                if i + 1 < len(elements) and elements[i+1]['type'] == 'underscore':
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
                    elements[i+1]['type'] == 'note' and 
                    elements[i+2]['type'] == 'underscore'):
                    note_char = elements[i+1]['char']
                    note_num, octave = self._get_note_gspn(note_char)
                    
                    notes_to_output.append({
                        'note_num': note_num,
                        'octave': octave,
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
                note_num, octave = self._get_note_gspn(note_char)
                note_value = ''
                
                # Check if followed by underscore (X_ pattern)
                if i + 1 < len(elements) and elements[i+1]['type'] == 'underscore':
                    note_value = 'A'
                
                notes_to_output.append({
                    'note_num': note_num,
                    'octave': octave,
                    'value': note_value,
                    'original_index': i
                })
                i += 1
                continue
            
            i += 1
        
        return notes_to_output
    
    def _apply_legato_markers(self, elements: List[Dict], notes_to_output: List[Dict]):
        """
        Apply legato markers to notes based on legato start/end markers.
        
        Args:
            elements: Parsed notation elements
            notes_to_output: List of notes to modify in-place
        """
        legato_count = 0
        legato_index = 0
        cross_line_legato = False
        cross_line_note_count = 0
        note_output_index = 0
        
        i = 0
        while i < len(elements):
            elem = elements[i]
            
            # Handle legato start markers
            if elem['type'] == 'legato_start':
                if elem['char'] in ['Î', 'Ë']:
                    legato_count = 2
                    legato_index = 0
                elif elem['char'] == 'Ï':
                    legato_count = 3
                    legato_index = 0
                elif elem['char'] == 'Õ':
                    legato_count = 4
                    legato_index = 0
                elif elem['char'] == '«':
                    cross_line_legato = True
                    cross_line_note_count = 0
                i += 1
                continue
            
            # Handle legato end marker
            if elem['type'] == 'legato_end':
                if note_output_index > 0:
                    note_idx = note_output_index - 1
                    if note_idx < len(notes_to_output):
                        current_legato = notes_to_output[note_idx].get('legato', '')
                        
                        if 'y' not in current_legato:
                            if current_legato == 'x':
                                notes_to_output[note_idx]['legato'] = 'y'
                            else:
                                notes_to_output[note_idx]['legato'] = current_legato + 'y'
                
                cross_line_legato = False
                cross_line_note_count = 0
                i += 1
                continue
            
            # Skip spaces
            if elem['type'] == 'space':
                i += 1
                continue
            
            # Determine if this element triggers a note output
            is_output_trigger = False
            
            if elem['type'] == 'rest':
                is_output_trigger = True
            elif elem['type'] == 'note':
                if i == 0 or elements[i-1]['type'] != 'underscore':
                    is_output_trigger = True
            elif elem['type'] == 'underscore':
                if (i + 2 < len(elements) and 
                    elements[i+1]['type'] == 'note' and 
                    elements[i+2]['type'] == 'underscore'):
                    is_output_trigger = True
            
            if is_output_trigger and note_output_index < len(notes_to_output):
                note = notes_to_output[note_output_index]
                
                # Add legato marker
                legato = ''
                if legato_count > 0:
                    if legato_index == 0:
                        legato = 'x'
                    elif legato_index == legato_count - 1:
                        legato = 'y'
                    legato_index += 1
                    if legato_index >= legato_count:
                        legato_count = 0
                        legato_index = 0
                elif cross_line_legato:
                    if cross_line_note_count == 0:
                        legato = 'x'
                    cross_line_note_count += 1
                
                note['legato'] = legato
                note_output_index += 1
            
            i += 1
