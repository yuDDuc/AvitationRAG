import os
from typing import List

class ApiKeyManager:
    def __init__(self):
        self.keys: List[str] = self._load_keys()
        self.current_idx = 0

    def _load_keys(self) -> List[str]:
        keys_str = os.getenv("GOOGLE_API_KEYS", "")
        # fallback to singular if plural not found
        if not keys_str:
            keys_str = os.getenv("GOOGLE_API_KEY", "")
            
        keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        return keys

    def get_next_key(self) -> str:
        """
        Returns the next API key in a round-robin fashion to distribute RPM.
        """
        if not self.keys:
            return ""
        
        key = self.keys[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.keys)
        return key

    def num_keys(self) -> int:
        return len(self.keys)

api_key_manager = ApiKeyManager()
