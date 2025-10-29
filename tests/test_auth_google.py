import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow

# Test module for auth/google.py


class TestAuthGoogle:
    """Test suite for auth/google.py module"""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        settings = Mock()
        settings.production = False
        settings.local = True
        settings.project_id = 'test-project'
        with patch('auth.google.SETTINGS', settings):
            yield settings

    @pytest.fixture
    def mock_flow(self):
        """Mock google auth flow"""
        flow = Mock(spec=google_auth_oauthlib.flow.Flow)
        flow.redirect_uri = 'http://127.0.0.1:8000/auth/google/callback'
        flow.authorization_url.return_value = ('https://accounts.google.com/auth', 'test-state-123')
        flow.credentials = Mock()
        flow.credentials.token = 'test-token'
        flow.credentials.refresh_token = 'test-refresh-token'
        flow.credentials.token_uri = 'https://oauth2.googleapis.com/token'
        flow.credentials.client_id = 'test-client-id'
        flow.credentials.client_secret = 'test-client-secret'
        flow.credentials.granted_scopes = ['scope1', 'scope2']
        return flow

    @pytest.fixture
    def mock_credentials(self):
        """Mock credentials dict"""
        return {
            'token': 'test-token',
            'refresh_token': 'test-refresh-token',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret',
            'granted_scopes': ['scope1', 'scope2']
        }

    @pytest.fixture
    def mock_user_info(self):
        """Mock user info response"""
        return {
            'id': '123456789',
            'email': 'test@example.com',
            'verified_email': True,
            'name': 'Test User',
            'given_name': 'Test',
            'family_name': 'User',
            'picture': 'https://example.com/photo.jpg'
        }


class TestGetAuthorizationUrl(TestAuthGoogle):
    """Tests for get_authorization_url function"""

    @patch('auth.google.google_auth_oauthlib.flow.Flow')
    def test_local_environment(self, mock_flow_class, mock_settings):
        """Test authorization URL generation in local environment"""
        from auth.google import get_authorization_url
        
        mock_settings.local = True
        mock_settings.production = False
        
        mock_flow = Mock()
        mock_flow.authorization_url.return_value = ('https://accounts.google.com/auth', 'test-state')
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        
        url, state = get_authorization_url()
        
        assert url == 'https://accounts.google.com/auth'
        assert state == 'test-state'
        assert mock_flow.redirect_uri == 'http://127.0.0.1:8000/auth/google/callback'
        mock_flow.authorization_url.assert_called_once_with(
            access_type='offline',
            prompt='consent'
        )

    @patch('auth.google.google_auth_oauthlib.flow.Flow')
    @patch('os.path.exists', return_value=True)
    def test_dev_environment(self, mock_exists, mock_flow_class, mock_settings):
        """Test authorization URL generation in dev environment"""
        from auth.google import get_authorization_url
        
        mock_settings.local = False
        mock_settings.production = False
        
        mock_flow = Mock()
        mock_flow.authorization_url.return_value = ('https://accounts.google.com/auth', 'test-state')
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        
        url, state = get_authorization_url()
        
        assert url == 'https://accounts.google.com/auth'
        assert state == 'test-state'
        assert mock_flow.redirect_uri == 'https://dev.api.odai.com/auth/google/callback'

    @patch('auth.google.access_secret_version')
    @patch('auth.google.google_auth_oauthlib.flow.Flow')
    def test_production_environment(self, mock_flow_class, mock_access_secret, mock_settings):
        """Test authorization URL generation in production environment"""
        from auth.google import get_authorization_url
        
        mock_settings.local = False
        mock_settings.production = True
        
        mock_credentials = {'web': {'client_id': 'prod-client', 'client_secret': 'prod-secret'}}
        mock_access_secret.return_value = json.dumps(mock_credentials)
        
        mock_flow = Mock()
        mock_flow.authorization_url.return_value = ('https://accounts.google.com/auth', 'prod-state')
        mock_flow_class.from_client_config.return_value = mock_flow
        
        url, state = get_authorization_url()
        
        assert url == 'https://accounts.google.com/auth'
        assert state == 'prod-state'
        assert mock_flow.redirect_uri == 'https://api.odai.com/auth/google/callback'
        mock_access_secret.assert_called_once_with('test-project', 'google_oauth_credentials')

    @patch('auth.google.access_secret_version')
    @patch('auth.google.google_auth_oauthlib.flow.Flow')
    def test_production_no_credentials_error(self, mock_flow_class, mock_access_secret, mock_settings):
        """Test error when no credentials found in production"""
        from auth.google import get_authorization_url
        
        mock_settings.production = True
        mock_settings.local = False
        mock_access_secret.return_value = None
        
        with pytest.raises(ValueError, match='No Google OAuth credentials found'):
            get_authorization_url()


class TestExchangeCodeForCredentials(TestAuthGoogle):
    """Tests for exchange_code_for_credentials function"""

    @patch('auth.google.google_auth_oauthlib.flow.Flow')
    @patch('os.path.exists', return_value=True)
    def test_local_environment(self, mock_exists, mock_flow_class, mock_settings, mock_flow):
        """Test code exchange in local environment"""
        from auth.google import exchange_code_for_credentials
        
        mock_settings.local = True
        mock_settings.production = False
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        
        auth_response = 'http://127.0.0.1:8000/auth/google/callback?code=test-code&state=test-state'
        result = exchange_code_for_credentials(auth_response)
        
        assert result['token'] == 'test-token'
        assert result['refresh_token'] == 'test-refresh-token'
        assert mock_flow.redirect_uri == 'http://127.0.0.1:8000/auth/google/callback'
        mock_flow.fetch_token.assert_called_once_with(authorization_response=auth_response)

    @patch('auth.google.google_auth_oauthlib.flow.Flow')
    @patch('os.path.exists', return_value=True)
    def test_dev_environment(self, mock_exists, mock_flow_class, mock_settings, mock_flow):
        """Test code exchange in dev environment"""
        from auth.google import exchange_code_for_credentials
        
        mock_settings.local = False
        mock_settings.production = False
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        mock_flow.redirect_uri = 'https://dev.api.odai.com/auth/google/callback'
        
        auth_response = 'https://dev.api.odai.com/auth/google/callback?code=test-code&state=test-state'
        result = exchange_code_for_credentials(auth_response)
        
        assert mock_flow.redirect_uri == 'https://dev.api.odai.com/auth/google/callback'
        mock_flow.fetch_token.assert_called_once_with(authorization_response=auth_response)

    @patch('auth.google.access_secret_version')
    @patch('auth.google.google_auth_oauthlib.flow.Flow')
    def test_production_environment(self, mock_flow_class, mock_access_secret, mock_settings, mock_flow):
        """Test code exchange in production environment"""
        from auth.google import exchange_code_for_credentials
        
        mock_settings.local = False
        mock_settings.production = True
        
        mock_credentials = {'web': {'client_id': 'prod-client', 'client_secret': 'prod-secret'}}
        mock_access_secret.return_value = json.dumps(mock_credentials)
        mock_flow_class.from_client_config.return_value = mock_flow
        
        auth_response = 'https://api.odai.com/auth/google/callback?code=test-code&state=test-state'
        result = exchange_code_for_credentials(auth_response)
        
        assert mock_flow.redirect_uri == 'https://api.odai.com/auth/google/callback'
        mock_flow.fetch_token.assert_called_once_with(authorization_response=auth_response)

    @patch('auth.google.access_secret_version')
    @patch('auth.google.google_auth_oauthlib.flow.Flow')
    def test_production_no_credentials_error(self, mock_flow_class, mock_access_secret, mock_settings):
        """Test error when no credentials found in production"""
        from auth.google import exchange_code_for_credentials
        
        mock_settings.production = True
        mock_settings.local = False
        mock_access_secret.return_value = None
        
        with pytest.raises(ValueError, match='No Google OAuth credentials found'):
            exchange_code_for_credentials('http://test.com/callback?code=test-code')


class TestGetUserInfo(TestAuthGoogle):
    """Tests for get_user_info function"""

    @patch('auth.google.build')
    @patch('auth.google.Credentials.from_authorized_user_info')
    def test_get_user_info_success(self, mock_creds_from_info, mock_build, mock_credentials, mock_user_info):
        """Test successful user info retrieval"""
        from auth.google import get_user_info
        
        mock_creds = Mock()
        mock_creds_from_info.return_value = mock_creds
        
        mock_service = Mock()
        mock_userinfo = Mock()
        mock_userinfo.get.return_value.execute.return_value = mock_user_info
        mock_service.userinfo.return_value = mock_userinfo
        mock_build.return_value = mock_service
        
        result = get_user_info(mock_credentials)
        
        assert result == mock_user_info
        mock_creds_from_info.assert_called_once_with(mock_credentials)
        mock_build.assert_called_once_with('oauth2', 'v2', credentials=mock_creds)

    @patch('auth.google.build')
    @patch('auth.google.Credentials.from_authorized_user_info')
    def test_get_user_info_api_error(self, mock_creds_from_info, mock_build, mock_credentials):
        """Test API error during user info retrieval"""
        from auth.google import get_user_info
        
        mock_creds = Mock()
        mock_creds_from_info.return_value = mock_creds
        
        mock_service = Mock()
        mock_service.userinfo.return_value.get.return_value.execute.side_effect = Exception("API Error")
        mock_build.return_value = mock_service
        
        with pytest.raises(Exception, match="API Error"):
            get_user_info(mock_credentials)


class TestCredentialsToDict(TestAuthGoogle):
    """Tests for credentials_to_dict function"""

    def test_credentials_to_dict_all_fields(self):
        """Test converting credentials object to dict with all fields"""
        from auth.google import credentials_to_dict
        
        mock_creds = Mock()
        mock_creds.token = 'access-token'
        mock_creds.refresh_token = 'refresh-token'
        mock_creds.token_uri = 'https://oauth2.googleapis.com/token'
        mock_creds.client_id = 'client-id'
        mock_creds.client_secret = 'client-secret'
        mock_creds.granted_scopes = ['scope1', 'scope2', 'scope3']
        
        result = credentials_to_dict(mock_creds)
        
        assert result == {
            'token': 'access-token',
            'refresh_token': 'refresh-token',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'client-id',
            'client_secret': 'client-secret',
            'granted_scopes': ['scope1', 'scope2', 'scope3']
        }

    def test_credentials_to_dict_missing_fields(self):
        """Test converting credentials object with None fields"""
        from auth.google import credentials_to_dict
        
        mock_creds = Mock()
        mock_creds.token = 'access-token'
        mock_creds.refresh_token = None
        mock_creds.token_uri = 'https://oauth2.googleapis.com/token'
        mock_creds.client_id = 'client-id'
        mock_creds.client_secret = 'client-secret'
        mock_creds.granted_scopes = []
        
        result = credentials_to_dict(mock_creds)
        
        assert result == {
            'token': 'access-token',
            'refresh_token': None,
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'client-id',
            'client_secret': 'client-secret',
            'granted_scopes': []
        }


class TestEnvironmentVariables(TestAuthGoogle):
    """Tests for environment variable configuration"""

    def test_non_production_env_vars(self, mock_settings):
        """Test environment variables set in non-production"""
        mock_settings.production = False
        
        # Re-import to trigger module-level code
        import importlib
        import auth.google
        importlib.reload(auth.google)
        
        assert os.environ.get('OAUTHLIB_INSECURE_TRANSPORT') == '1'
        assert os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE') == '1'

    def test_production_env_vars(self, mock_settings):
        """Test environment variables set in production"""
        mock_settings.production = True
        
        # Re-import to trigger module-level code
        import importlib
        import auth.google
        importlib.reload(auth.google)
        
        # Even in production, these are set to '1' based on the code
        assert os.environ.get('OAUTHLIB_INSECURE_TRANSPORT') == '1'
        assert os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE') == '1'


class TestScopes(TestAuthGoogle):
    """Test OAuth scopes configuration"""

    def test_required_scopes(self):
        """Test that all required scopes are present"""
        from auth.google import SCOPES
        
        expected_scopes = [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/calendar.events.owned',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/docs',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/presentations.readonly'
        ]
        
        assert SCOPES == expected_scopes
        assert len(SCOPES) == 10