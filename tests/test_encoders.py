"""
Tests for encoding strategies.
"""

import pytest
from abiyasa.encoders import GSPNEncoder, QAPEncoder


class TestGSPNEncoder:
    """Tests for GSPN encoder."""
    
    def test_basic_encoding_balungan(self):
        """Test basic GSPN encoding with Balungan notation."""
        encoder = GSPNEncoder(notation_system='balungan')
        
        # Test simple sequences
        assert encoder.encode("- - - -") == "0000"
        assert encoder.encode("F F") == "6a6a"
        assert encoder.encode("H I J") == "123"
    
    def test_encoding_with_values(self):
        """Test GSPN encoding with note values."""
        encoder = GSPNEncoder(notation_system='balungan')
        
        # Test half values
        assert encoder.encode("-_ _F_") == "0A6aA"
    
    def test_encoding_with_legato(self):
        """Test GSPN encoding with legato markers."""
        encoder = GSPNEncoder(notation_system='balungan')
        
        # Test legato patterns
        assert encoder.encode("ÎI J") == "2x3y"
    
    def test_kepatihan_notation(self):
        """Test GSPN encoding with Kepatihan notation."""
        encoder = GSPNEncoder(notation_system='kepatihan')
        
        # Test basic notes
        assert encoder.encode(". . . .") == "0000"
        assert encoder.encode("1 2 3") == "123"
    
    def test_encoder_info(self):
        """Test encoder metadata."""
        encoder = GSPNEncoder(notation_system='balungan')
        
        info = encoder.get_info()
        assert info['name'] == 'GSPN'
        assert info['notation_system'] == 'balungan'
        assert 'type' in info


class TestQAPEncoder:
    """Tests for QAP encoder."""
    
    def test_not_implemented(self):
        """Test that QAP encoder raises NotImplementedError."""
        encoder = QAPEncoder(notation_system='balungan')
        
        with pytest.raises(NotImplementedError):
            encoder.encode("H I J")
        
        with pytest.raises(NotImplementedError):
            encoder.decode("123")
    
    def test_encoder_name(self):
        """Test QAP encoder name."""
        encoder = QAPEncoder(notation_system='balungan')
        assert encoder.name == 'QAP'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
