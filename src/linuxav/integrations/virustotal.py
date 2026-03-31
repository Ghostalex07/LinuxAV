import requests
import logging
from typing import Dict, Optional


class VirusTotalClient:
    def __init__(self, api_key: Optional[str] = None):
        self.logger = logging.getLogger("linuxav.virustotal")
        self.api_key = api_key
        self.base_url = "https://www.virustotal.com/api/v3"
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"x-apikey": api_key})

    def check_file(self, file_hash: str) -> Optional[Dict]:
        if not self.api_key:
            self.logger.warning("API key not configured")
            return None

        url = f"{self.base_url}/files/{file_hash}"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"VirusTotal query error: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")

        return None
