"""AES-256-GCM Encryption for Golem Assets"""
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from typing import Dict, Optional
import os
import json
import base64


class GolemAssetEncryption:
    """Encrypt/decrypt assets for Golem regional distribution"""
    
    def __init__(self, master_key: str):
        self.backend = default_backend()
        self.master_key = master_key.encode()
    
    def encrypt_asset(self, asset_data: bytes, region: str = None, metadata: Dict = None) -> Dict:
        """Encrypt asset with AES-256-GCM for regional transmission
        
        Args:
            asset_data: Binary asset data to encrypt
            region: Target region (e.g., 'east-1', 'east-2')
            metadata: Optional metadata to include
        
        Returns:
            Dictionary with encrypted payload and keys
        """
        salt = os.urandom(16)
        iv = os.urandom(12)
        
        # Derive key from master key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        key = kdf.derive(self.master_key)
        
        # AES-256-GCM encryption
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(asset_data) + encryptor.finalize()
        
        encrypted_payload = {
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "tag": base64.b64encode(encryptor.tag).decode('utf-8'),
            "iv": base64.b64encode(iv).decode('utf-8'),
            "salt": base64.b64encode(salt).decode('utf-8'),
            "region": region or "default",
            "algorithm": "AES-256-GCM",
            "iterations": 100000,
            "metadata": metadata or {}
        }
        
        return encrypted_payload
    
    def decrypt_asset(self, encrypted_data: Dict) -> bytes:
        """Decrypt asset received from regional nodes
        
        Args:
            encrypted_data: Encrypted payload dictionary
        
        Returns:
            Decrypted binary data
        """
        try:
            salt = base64.b64decode(encrypted_data["salt"])
            iv = base64.b64decode(encrypted_data["iv"])
            tag = base64.b64decode(encrypted_data["tag"])
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            
            # Derive same key
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=encrypted_data.get("iterations", 100000),
                backend=self.backend
            )
            key = kdf.derive(self.master_key)
            
            # AES-256-GCM decryption
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    @staticmethod
    def encrypt_file(file_path: str, master_key: str, region: str = None) -> str:
        """Encrypt a file and save encrypted version"""
        encryptor = GolemAssetEncryption(master_key)
        with open(file_path, 'rb') as f:
            data = f.read()
        encrypted = encryptor.encrypt_asset(data, region)
        output_path = f"{file_path}.encrypted"
        with open(output_path, 'w') as f:
            json.dump(encrypted, f)
        return output_path
    
    @staticmethod
    def decrypt_file(encrypted_file_path: str, master_key: str) -> bytes:
        """Decrypt an encrypted file"""
        encryptor = GolemAssetEncryption(master_key)
        with open(encrypted_file_path, 'r') as f:
            encrypted_data = json.load(f)
        return encryptor.decrypt_asset(encrypted_data)
