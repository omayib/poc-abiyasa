"""
File downloading utilities for gamelan datasets.
"""

import os
from pathlib import Path
import requests


def download_gamelan_file(
    url: str,
    local_path: Path,
    timeout: int = 30,
    force_download: bool = False
) -> Path:
    """
    Download a gamelan PDF file from URL.
    
    Args:
        url: URL of the file to download
        local_path: Local path where file should be saved
        timeout: Request timeout in seconds
        force_download: If True, re-download even if file exists
        
    Returns:
        Path object pointing to the downloaded file
        
    Raises:
        requests.RequestException: If download fails
    """
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    if local_path.exists() and not force_download:
        return local_path
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        return local_path
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error downloading file from {url}: {e}")
