"""
Base encoder interface for gamelan notation encoding strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseEncoder(ABC):
    """
    Abstract base class for all encoding strategies.
    
    Encoders convert gamelan notation sequences into specific formats
    like GSPN, QAP, or other representations.
    """
    
    def __init__(self, notation_system: str = 'balungan'):
        """
        Initialize the encoder.
        
        Args:
            notation_system: The notation system to use ('balungan' or 'kepatihan')
        """
        self.notation_system = notation_system
    
    @abstractmethod
    def encode(self, sequence: str) -> str:
        """
        Encode a sequence string into the target format.
        
        Args:
            sequence: Input notation sequence string
            
        Returns:
            Encoded string in the target format
        """
        pass
    
    @abstractmethod
    def decode(self, encoded: str) -> str:
        """
        Decode an encoded string back to notation sequence.
        
        Args:
            encoded: Encoded string
            
        Returns:
            Original notation sequence string
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this encoding strategy."""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this encoder.
        
        Returns:
            Dictionary containing encoder metadata
        """
        return {
            'name': self.name,
            'notation_system': self.notation_system,
            'type': self.__class__.__name__
        }
