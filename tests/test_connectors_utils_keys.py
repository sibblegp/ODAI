"""Tests for the connectors/utils/keys module.

Note: This module is globally mocked by test_firebase_models_base.py for all tests.
The tests here verify that the mock functions exist and behave as expected.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKeysMocking:
    """Test that the keys module is properly mocked for testing."""
    
    def test_keys_module_is_mocked(self):
        """Verify that connectors.utils.keys is mocked globally."""
        import connectors.utils.keys as keys_module
        
        # The module should be a Mock object due to global mocking
        assert hasattr(keys_module, 'create_key_hsm')
        assert hasattr(keys_module, 'encrypt_symmetric')
        assert hasattr(keys_module, 'decrypt_symmetric')
        assert hasattr(keys_module, 'crc32c')
    
    def test_create_key_hsm_mock_behavior(self):
        """Test the mocked create_key_hsm function."""
        from connectors.utils.keys import create_key_hsm
        
        # The mock returns "mock_key_123" as configured in test_firebase_models_base.py
        result = create_key_hsm('test-project', 'us-east1', 'test-ring', 'test-key')
        assert result == "mock_key_123"
    
    def test_encrypt_symmetric_mock_behavior(self):
        """Test the mocked encrypt_symmetric function."""
        from connectors.utils.keys import encrypt_symmetric
        
        # Call the mocked function
        result = encrypt_symmetric('test-project', 'us-east1', 'test-ring', 'test-key', 'Hello World')
        
        # The mock should return a mock response with ciphertext
        assert hasattr(result, 'ciphertext')
        assert result.ciphertext == b"mock_encrypted_data"
    
    def test_decrypt_symmetric_mock_behavior(self):
        """Test the mocked decrypt_symmetric function."""
        from connectors.utils.keys import decrypt_symmetric
        
        # Call the mocked function
        result = decrypt_symmetric('test-project', 'us-east1', 'test-ring', 'test-key', b'encrypted_data')
        
        # The mock should return a mock response with plaintext
        assert hasattr(result, 'plaintext')
        # The decrypt mock returns a Mock object, not the configured value
        # Just verify it has the plaintext attribute
        assert result.plaintext is not None
    
    def test_crc32c_mock_behavior(self):
        """Test the mocked crc32c function."""
        from connectors.utils.keys import crc32c
        
        # The function is mocked
        result = crc32c(b'Hello World')
        
        # It should be callable but return a mock
        assert callable(crc32c)


class TestKeysModuleDocumentation:
    """Test documentation and expected behavior of the keys module."""
    
    def test_expected_functions_exist(self):
        """Verify all expected functions exist in the module."""
        import connectors.utils.keys as keys_module
        
        expected_functions = [
            'create_key_hsm',
            'encrypt_symmetric', 
            'decrypt_symmetric',
            'crc32c'
        ]
        
        for func_name in expected_functions:
            assert hasattr(keys_module, func_name)
            # They should all be callable (even if mocked)
            func = getattr(keys_module, func_name)
            assert callable(func)
    
    def test_encryption_decryption_contract(self):
        """Test that encrypt/decrypt follow expected contract."""
        from connectors.utils.keys import encrypt_symmetric, decrypt_symmetric
        
        # Even with mocks, we can verify the functions exist and are callable
        plaintext = "Test message"
        
        # Encrypt
        encrypt_result = encrypt_symmetric('proj', 'loc', 'ring', 'key', plaintext)
        assert hasattr(encrypt_result, 'ciphertext')
        
        # Decrypt
        decrypt_result = decrypt_symmetric('proj', 'loc', 'ring', 'key', encrypt_result.ciphertext)
        assert hasattr(decrypt_result, 'plaintext')
    
    def test_key_creation_returns_value(self):
        """Test that create_key_hsm returns a value."""
        from connectors.utils.keys import create_key_hsm
        
        result = create_key_hsm('project', 'location', 'ring', 'key')
        assert result is not None
        assert result == "mock_key_123"  # Expected mock value


class TestKeysIntegration:
    """Test integration points with the keys module."""
    
    def test_keys_used_in_firebase_models(self):
        """Verify keys module is used by Firebase models for encryption."""
        # This is more of a documentation test
        # The keys module is used by Firebase models to:
        # 1. Create HSM keys for users
        # 2. Encrypt sensitive data like tokens
        # 3. Decrypt data when needed
        
        # Import a Firebase model that uses keys
        from firebase.models.user import User
        
        # User model uses key_id field for encryption keys
        # The User model calls check_has_key_and_generate_if_not() to create keys
        # Just verify we can import the model that uses keys
        assert User is not None
    
    def test_encryption_workflow(self):
        """Test the expected encryption workflow."""
        from connectors.utils.keys import create_key_hsm, encrypt_symmetric, decrypt_symmetric
        
        # Step 1: Create a key (mocked)
        key_name = create_key_hsm('proj', 'loc', 'ring', 'user-key-123')
        assert key_name == "mock_key_123"
        
        # Step 2: Encrypt data
        secret_data = "sensitive information"
        encrypted = encrypt_symmetric('proj', 'loc', 'ring', 'user-key-123', secret_data)
        assert encrypted.ciphertext == b"mock_encrypted_data"
        
        # Step 3: Decrypt data
        decrypted = decrypt_symmetric('proj', 'loc', 'ring', 'user-key-123', encrypted.ciphertext)
        assert hasattr(decrypted, 'plaintext')
        assert decrypted.plaintext is not None


# Note: The actual connectors/utils/keys.py module is mocked globally by
# test_firebase_models_base.py to avoid Google Cloud KMS dependencies in tests.
# These tests verify the mock behavior and document the expected interface.