import pytest
from unittest.mock import Mock, patch, MagicMock
import json

# Integration tests for Google auth (auth/google.py + routers/google.py)


class TestGoogleAuthIntegration:
    """Integration tests for the Google OAuth flow"""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings"""
        settings = Mock()
        settings.production = False
        settings.local = False
        settings.project_id = 'test-project'
        return settings

    @pytest.fixture
    def mock_flow(self):
        """Mock OAuth flow"""
        flow = Mock()
        flow.authorization_url.return_value = ('https://accounts.google.com/auth', 'test-state')
        flow.credentials = Mock(
            token='access-token',
            refresh_token='refresh-token',
            token_uri='https://oauth2.googleapis.com/token',
            client_id='test-client',
            client_secret='test-secret',
            granted_scopes=['scope1', 'scope2']
        )
        return flow

    def test_oauth_flow_redirect_uris(self, mock_settings):
        """Test that redirect URIs are correctly set based on environment"""
        with patch('auth.google.SETTINGS', mock_settings):
            from auth.google import get_authorization_url
            
            # Test local environment
            mock_settings.local = True
            mock_settings.production = False
            with patch('auth.google.google_auth_oauthlib.flow.Flow') as mock_flow_class:
                mock_flow = Mock()
                mock_flow.authorization_url.return_value = ('url', 'state')
                mock_flow_class.from_client_secrets_file.return_value = mock_flow
                
                get_authorization_url()
                assert mock_flow.redirect_uri == 'http://127.0.0.1:8000/auth/google/callback'
            
            # Test dev environment
            mock_settings.local = False
            mock_settings.production = False
            with patch('auth.google.google_auth_oauthlib.flow.Flow') as mock_flow_class:
                mock_flow = Mock()
                mock_flow.authorization_url.return_value = ('url', 'state')
                mock_flow_class.from_client_secrets_file.return_value = mock_flow
                
                get_authorization_url()
                assert mock_flow.redirect_uri == 'https://dev.api.odai.com/auth/google/callback'
            
            # Test production environment
            mock_settings.local = False
            mock_settings.production = True
            with patch('auth.google.access_secret_version') as mock_access_secret:
                mock_access_secret.return_value = json.dumps({'web': {'client_id': 'prod', 'client_secret': 'secret'}})
                with patch('auth.google.google_auth_oauthlib.flow.Flow') as mock_flow_class:
                    mock_flow = Mock()
                    mock_flow.authorization_url.return_value = ('url', 'state')
                    mock_flow_class.from_client_config.return_value = mock_flow
                    
                    get_authorization_url()
                    assert mock_flow.redirect_uri == 'https://api.odai.com/auth/google/callback'

    def test_full_oauth_flow(self, mock_settings, mock_flow):
        """Test the complete OAuth flow from authorization to token exchange"""
        with patch('auth.google.SETTINGS', mock_settings):
            with patch('auth.google.google_auth_oauthlib.flow.Flow') as mock_flow_class:
                mock_flow_class.from_client_secrets_file.return_value = mock_flow
                
                # Step 1: Get authorization URL
                from auth.google import get_authorization_url
                auth_url, state = get_authorization_url()
                
                assert auth_url == 'https://accounts.google.com/auth'
                assert state == 'test-state'
                
                # Step 2: Exchange code for credentials
                from auth.google import exchange_code_for_credentials
                auth_response = 'http://127.0.0.1:8000/auth/google/callback?code=auth-code&state=test-state'
                
                credentials = exchange_code_for_credentials(auth_response)
                
                assert credentials['token'] == 'access-token'
                assert credentials['refresh_token'] == 'refresh-token'
                mock_flow.fetch_token.assert_called_once_with(authorization_response=auth_response)
                
                # Step 3: Get user info
                from auth.google import get_user_info
                with patch('auth.google.build') as mock_build:
                    mock_service = Mock()
                    mock_service.userinfo.return_value.get.return_value.execute.return_value = {
                        'id': '123',
                        'email': 'test@example.com',
                        'name': 'Test User'
                    }
                    mock_build.return_value = mock_service
                    
                    user_info = get_user_info(credentials)
                    
                    assert user_info['email'] == 'test@example.com'
                    assert user_info['name'] == 'Test User'

    def test_scopes_configuration(self):
        """Test that all required scopes are configured"""
        from auth.google import SCOPES
        
        required_scopes = [
            'userinfo.email',
            'userinfo.profile',
            'calendar.events.owned',
            'gmail.send',
            'gmail.modify',
            'documents',
            'docs',
            'drive',
            'spreadsheets.readonly',
            'presentations.readonly'
        ]
        
        for scope in required_scopes:
            assert any(scope in s for s in SCOPES), f"Missing scope: {scope}"

    def test_error_handling(self, mock_settings):
        """Test error handling in the OAuth flow"""
        with patch('auth.google.SETTINGS', mock_settings):
            mock_settings.production = True
            mock_settings.local = False
            
            # Test missing credentials in production
            with patch('auth.google.access_secret_version') as mock_access_secret:
                mock_access_secret.return_value = None
                
                from auth.google import get_authorization_url
                with pytest.raises(ValueError, match='No Google OAuth credentials found'):
                    get_authorization_url()
            
            # Test API error during user info retrieval
            from auth.google import get_user_info
            with patch('auth.google.Credentials.from_authorized_user_info') as mock_creds_from_info:
                mock_creds = Mock()
                mock_creds_from_info.return_value = mock_creds
                
                with patch('auth.google.build') as mock_build:
                    mock_service = Mock()
                    mock_service.userinfo.return_value.get.return_value.execute.side_effect = Exception("API Error")
                    mock_build.return_value = mock_service
                    
                    valid_credentials = {
                        'token': 'access-token',
                        'refresh_token': 'refresh-token',
                        'client_id': 'client-id',
                        'client_secret': 'client-secret'
                    }
                    
                    with pytest.raises(Exception, match="API Error"):
                        get_user_info(valid_credentials)

    def test_credentials_transformation(self):
        """Test the credentials_to_dict function"""
        from auth.google import credentials_to_dict
        
        # Create mock credentials
        mock_creds = Mock()
        mock_creds.token = 'access-token'
        mock_creds.refresh_token = 'refresh-token'
        mock_creds.token_uri = 'https://oauth2.googleapis.com/token'
        mock_creds.client_id = 'client-id'
        mock_creds.client_secret = 'client-secret'
        mock_creds.granted_scopes = ['scope1', 'scope2']
        
        result = credentials_to_dict(mock_creds)
        
        assert result == {
            'token': 'access-token',
            'refresh_token': 'refresh-token',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'client-id',
            'client_secret': 'client-secret',
            'granted_scopes': ['scope1', 'scope2']
        }

    def test_environment_variables_setup(self):
        """Test that environment variables are set correctly"""
        import os
        # These are set at module import time
        assert os.environ.get('OAUTHLIB_INSECURE_TRANSPORT') == '1'
        assert os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE') == '1'