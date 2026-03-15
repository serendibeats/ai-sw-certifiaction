import base64
from exceptions import EncryptionError


class EncryptionManager:
    def __init__(self, key: str):
        if not key:
            raise EncryptionError("Encryption key cannot be empty")
        self._key = key

    def encrypt(self, plaintext):
        if not plaintext:
            return plaintext
        key_bytes = self._key.encode('utf-8')
        plaintext_bytes = plaintext.encode('utf-8')
        encrypted = bytes([
            plaintext_bytes[i] ^ key_bytes[i % len(key_bytes)]
            for i in range(len(plaintext_bytes))
        ])
        encoded = base64.b64encode(encrypted).decode('utf-8')
        return f"ENC:{encoded}"

    def decrypt(self, ciphertext):
        if not ciphertext:
            return ciphertext
        if not self.is_encrypted(ciphertext):
            return ciphertext
        encoded = ciphertext[4:]  # Remove "ENC:" prefix
        encrypted = base64.b64decode(encoded)
        key_bytes = self._key.encode('utf-8')
        decrypted = bytes([
            encrypted[i] ^ key_bytes[i % len(key_bytes)]
            for i in range(len(encrypted))
        ])
        return decrypted.decode('utf-8')

    def is_encrypted(self, text):
        return isinstance(text, str) and text.startswith("ENC:")
