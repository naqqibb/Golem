"""Secure API Client for Golem Regional Distribution"""
import os
import json
import requests
from typing import Dict, Optional, Any
from .asset_encryption import GolemAssetEncryption
import ssl


class GolemRegionalAPIClient:
    """API client with encrypted payload transmission"""
    
    def __init__(self, master_key: str, region: str = "east-1"):
        self.encryption = GolemAssetEncryption(master_key)
        self.region = region
        self.session = requests.Session()
        self._setup_tls()
    
    def _setup_tls(self):
        """Configure TLS/SSL for secure transit"""
        # Force TLS 1.2+
        self.session.verify = True
        adapter = requests.adapters.HTTPAdapter(
            max_retries=requests.packages.urllib3.util.retry.Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        self.session.mount('https://', adapter)
    
    def get_endpoint_url(self) -> str:
        """Get regional API endpoint from environment secrets"""
        env_key = f"GOLEM_API_{self.region.upper()}"
        endpoint = os.getenv(env_key)
        if not endpoint:
            raise ValueError(f"Missing environment variable: {env_key}")
        return endpoint
    
    def get_api_credentials(self) -> Dict[str, str]:
        """Retrieve API credentials from GitHub Secrets"""
        credentials = {
            "api_key": os.getenv("GOLEM_API_KEY"),
            "api_secret": os.getenv("GOLEM_API_SECRET"),
            "region": self.region
        }
        if not credentials["api_key"] or not credentials["api_secret"]:
            raise ValueError("Missing API credentials in environment")
        return credentials
    
    def send_encrypted_asset(self, asset_data: bytes, asset_name: str, metadata: Dict = None) -> Dict:
        """Send encrypted asset to regional Golem node
        
        Args:
            asset_data: Binary asset data
            asset_name: Name/identifier for asset
            metadata: Optional metadata
        
        Returns:
            Response from API
        """
        try:
            # Encrypt asset
            encrypted_payload = self.encryption.encrypt_asset(
                asset_data,
                region=self.region,
                metadata=metadata or {"name": asset_name}
            )
            
            # Get credentials
            creds = self.get_api_credentials()
            
            # Prepare request
            headers = {
                "Authorization": f"Bearer {creds['api_key']}",
                "X-Region": self.region,
                "X-Asset-Name": asset_name,
                "Content-Type": "application/json"
            }
            
            endpoint = self.get_endpoint_url()
            
            # Send encrypted payload
            response = self.session.post(
                f"{endpoint}/assets/upload",
                json=encrypted_payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "message": "Asset encrypted and transmitted",
                "region": self.region,
                "asset_name": asset_name,
                "response": response.json()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "region": self.region
            }
    
    def retrieve_encrypted_asset(self, asset_id: str) -> Dict:
        """Retrieve encrypted asset from regional node
        
        Args:
            asset_id: ID of asset to retrieve
        
        Returns:
            Encrypted asset data
        """
        try:
            creds = self.get_api_credentials()
            headers = {
                "Authorization": f"Bearer {creds['api_key']}",
                "X-Region": self.region
            }
            
            endpoint = self.get_endpoint_url()
            response = self.session.get(
                f"{endpoint}/assets/{asset_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            encrypted_data = response.json()
            decrypted = self.encryption.decrypt_asset(encrypted_data)
            
            return {
                "success": True,
                "asset_id": asset_id,
                "data": decrypted,
                "region": self.region
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "asset_id": asset_id
            }
    
    def list_regional_assets(self) -> Dict:
        """List assets available in region"""
        try:
            creds = self.get_api_credentials()
            headers = {
                "Authorization": f"Bearer {creds['api_key']}",
                "X-Region": self.region
            }
            
            endpoint = self.get_endpoint_url()
            response = self.session.get(
                f"{endpoint}/assets",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "region": self.region,
                "assets": response.json()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "region": self.region
            }
