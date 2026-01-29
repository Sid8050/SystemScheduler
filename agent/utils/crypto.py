"""
Cryptography Utilities for Endpoint Security Agent

Provides encryption for:
- File backup encryption (AES-256-GCM)
- Configuration secrets
- API key management
"""

import os
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""
    ciphertext: bytes
    nonce: bytes
    salt: Optional[bytes] = None
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage."""
        # Format: salt_len(2) + salt + nonce_len(2) + nonce + ciphertext
        parts = []
        
        if self.salt:
            parts.append(len(self.salt).to_bytes(2, 'big'))
            parts.append(self.salt)
        else:
            parts.append((0).to_bytes(2, 'big'))
        
        parts.append(len(self.nonce).to_bytes(2, 'big'))
        parts.append(self.nonce)
        parts.append(self.ciphertext)
        
        return b''.join(parts)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'EncryptedData':
        """Deserialize from bytes."""
        offset = 0
        
        # Read salt
        salt_len = int.from_bytes(data[offset:offset+2], 'big')
        offset += 2
        salt = data[offset:offset+salt_len] if salt_len > 0 else None
        offset += salt_len
        
        # Read nonce
        nonce_len = int.from_bytes(data[offset:offset+2], 'big')
        offset += 2
        nonce = data[offset:offset+nonce_len]
        offset += nonce_len
        
        # Rest is ciphertext
        ciphertext = data[offset:]
        
        return cls(ciphertext=ciphertext, nonce=nonce, salt=salt)
    
    def to_base64(self) -> str:
        """Encode as base64 string."""
        return base64.b64encode(self.to_bytes()).decode('ascii')
    
    @classmethod
    def from_base64(cls, data: str) -> 'EncryptedData':
        """Decode from base64 string."""
        return cls.from_bytes(base64.b64decode(data))


class CryptoManager:
    """
    Encryption manager for file and data protection.
    
    Uses AES-256-GCM for authenticated encryption.
    """
    
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits for GCM
    SALT_SIZE = 16  # 128 bits
    
    def __init__(self, key: Optional[bytes] = None, key_file: Optional[Path] = None):
        """
        Initialize with encryption key.
        
        Args:
            key: Direct key bytes (32 bytes for AES-256)
            key_file: Path to file containing key
        """
        if key:
            self._key = key
        elif key_file and key_file.exists():
            self._key = self._load_key(key_file)
        else:
            self._key = None
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new random encryption key."""
        return secrets.token_bytes(CryptoManager.KEY_SIZE)
    
    @staticmethod
    def derive_key(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password string
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(CryptoManager.SALT_SIZE)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=CryptoManager.KEY_SIZE,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def _load_key(self, key_file: Path) -> bytes:
        """Load key from file."""
        with open(key_file, 'rb') as f:
            return f.read()
    
    def save_key(self, key_file: Path) -> None:
        """Save current key to file."""
        if self._key is None:
            raise ValueError("No key to save")
        
        key_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with restricted permissions
        with open(key_file, 'wb') as f:
            f.write(self._key)
        
        # Try to set permissions (Windows)
        try:
            import stat
            os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
    
    @property
    def has_key(self) -> bool:
        """Check if encryption key is available."""
        return self._key is not None
    
    def set_key(self, key: bytes) -> None:
        """Set the encryption key."""
        if len(key) != self.KEY_SIZE:
            raise ValueError(f"Key must be {self.KEY_SIZE} bytes")
        self._key = key
    
    def encrypt(self, plaintext: bytes) -> EncryptedData:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            EncryptedData container
        """
        if self._key is None:
            raise ValueError("No encryption key set")
        
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        return EncryptedData(ciphertext=ciphertext, nonce=nonce)
    
    def decrypt(self, encrypted: EncryptedData) -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        Args:
            encrypted: EncryptedData container
            
        Returns:
            Decrypted plaintext
        """
        if self._key is None:
            raise ValueError("No encryption key set")
        
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(encrypted.nonce, encrypted.ciphertext, None)
    
    def encrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Encrypt a file.
        
        Args:
            input_path: Path to file to encrypt
            output_path: Output path (defaults to input_path + .enc)
            
        Returns:
            Path to encrypted file
        """
        if output_path is None:
            output_path = input_path.with_suffix(input_path.suffix + '.enc')
        
        with open(input_path, 'rb') as f:
            plaintext = f.read()
        
        encrypted = self.encrypt(plaintext)
        
        with open(output_path, 'wb') as f:
            f.write(encrypted.to_bytes())
        
        return output_path
    
    def decrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Decrypt a file.
        
        Args:
            input_path: Path to encrypted file
            output_path: Output path (defaults to removing .enc suffix)
            
        Returns:
            Path to decrypted file
        """
        if output_path is None:
            if input_path.suffix == '.enc':
                output_path = input_path.with_suffix('')
            else:
                output_path = input_path.with_suffix('.dec')
        
        with open(input_path, 'rb') as f:
            encrypted = EncryptedData.from_bytes(f.read())
        
        plaintext = self.decrypt(encrypted)
        
        with open(output_path, 'wb') as f:
            f.write(plaintext)
        
        return output_path
    
    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string, returning base64-encoded result."""
        encrypted = self.encrypt(plaintext.encode('utf-8'))
        return encrypted.to_base64()
    
    def decrypt_string(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded encrypted string."""
        encrypted = EncryptedData.from_base64(ciphertext)
        plaintext = self.decrypt(encrypted)
        return plaintext.decode('utf-8')


class PasswordEncryption:
    """
    Password-based encryption for configuration secrets.
    
    Derives key from password using PBKDF2.
    """
    
    def __init__(self, password: str):
        """Initialize with password."""
        self.password = password
    
    def encrypt(self, plaintext: bytes) -> EncryptedData:
        """Encrypt data with password-derived key."""
        key, salt = CryptoManager.derive_key(self.password)
        
        nonce = secrets.token_bytes(CryptoManager.NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        return EncryptedData(ciphertext=ciphertext, nonce=nonce, salt=salt)
    
    def decrypt(self, encrypted: EncryptedData) -> bytes:
        """Decrypt data with password-derived key."""
        if encrypted.salt is None:
            raise ValueError("Salt required for password-based decryption")
        
        key, _ = CryptoManager.derive_key(self.password, encrypted.salt)
        
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(encrypted.nonce, encrypted.ciphertext, None)
    
    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt string with password."""
        encrypted = self.encrypt(plaintext.encode('utf-8'))
        return encrypted.to_base64()
    
    def decrypt_string(self, ciphertext: str) -> str:
        """Decrypt string with password."""
        encrypted = EncryptedData.from_base64(ciphertext)
        plaintext = self.decrypt(encrypted)
        return plaintext.decode('utf-8')


def hash_file(file_path: Path, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, etc.)
        
    Returns:
        Hex digest of hash
    """
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def secure_random_string(length: int = 32) -> str:
    """Generate a cryptographically secure random string."""
    return secrets.token_urlsafe(length)
