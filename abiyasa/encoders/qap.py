"""
QAP (Quantized Audio Pitch) Encoder - Placeholder

This is a placeholder for future QAP encoding implementation.
"""

from .base import BaseEncoder


class QAPEncoder(BaseEncoder):
    """
    QAP (Quantized Audio Pitch) encoder for gamelan music.
    
    This is a placeholder implementation for future development.
    """
    
    @property
    def name(self) -> str:
        return "QAP"
    
    def encode(self, sequence: str) -> str:
        """
        Encode sequence to QAP format.
        
        Args:
            sequence: Input notation sequence string
            
        Returns:
            QAP encoded string
        """
        raise NotImplementedError(
            "QAP encoding is not yet implemented. "
            "Please use GSPN encoder or contribute to the project!"
        )
    
    def decode(self, encoded: str) -> str:
        """
        Decode QAP format to sequence.
        
        Args:
            encoded: QAP encoded string
            
        Returns:
            Decoded notation sequence string
        """
        raise NotImplementedError(
            "QAP decoding is not yet implemented. "
            "Please use GSPN encoder or contribute to the project!"
        )
