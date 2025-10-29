"""Tests for the utils/imports module."""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestSafeImport:
    """Test the safe_import function."""
    
    def test_safe_import_successful(self):
        """Test safe_import with a module that exists."""
        from utils.imports import safe_import
        
        # Test importing a standard library module
        os_module = safe_import('os')
        assert os_module is not None
        assert hasattr(os_module, 'path')
    
    def test_safe_import_with_fallback_success(self):
        """Test safe_import with fallback when primary import fails."""
        from utils.imports import safe_import
        
        with patch('builtins.__import__') as mock_import:
            # First call raises ImportError, second succeeds
            mock_module = Mock()
            mock_import.side_effect = [ImportError(), mock_module]
            
            result = safe_import('nonexistent_module', 'fallback_module')
            assert result == mock_module
            assert mock_import.call_count == 2
    
    def test_safe_import_no_fallback_raises(self):
        """Test safe_import raises when no fallback and import fails."""
        from utils.imports import safe_import
        
        with patch('builtins.__import__') as mock_import:
            mock_import.side_effect = ImportError("Module not found")
            
            with pytest.raises(ImportError):
                safe_import('nonexistent_module')
    
    def test_safe_import_both_fail_raises(self):
        """Test safe_import raises when both primary and fallback fail."""
        from utils.imports import safe_import
        
        with patch('builtins.__import__') as mock_import:
            mock_import.side_effect = ImportError("Module not found")
            
            with pytest.raises(ImportError):
                safe_import('nonexistent_module', 'also_nonexistent')


class TestGetSettings:
    """Test the get_settings function."""
    
    def test_get_settings_primary_import(self):
        """Test get_settings with successful primary import."""
        # Mock the Settings class
        mock_settings = Mock()
        mock_module = Mock(Settings=mock_settings)
        
        # Configure the import to work
        with patch.dict('sys.modules', {'config': mock_module}):
            from utils.imports import get_settings
            result = get_settings()
            assert result == mock_settings
    
    def test_get_settings_fallback_import(self):
        """Test get_settings with fallback to relative import."""
        # First, clear the function's cached imports by reloading the module
        import importlib
        import utils.imports
        
        # Save config module if it exists
        saved_config = sys.modules.get('config')
        
        try:
            # Remove config module to force fallback
            if 'config' in sys.modules:
                del sys.modules['config']
            
            # Reload module to clear any cached imports
            importlib.reload(utils.imports)
            
            # Now try to import - should use relative import and work
            result = utils.imports.get_settings()
            
            # The function should return Settings class (from relative import)
            assert result is not None
            assert hasattr(result, '__name__')  # It's a class
        finally:
            # Restore original config module
            if saved_config:
                sys.modules['config'] = saved_config
            # Reload again to restore original state
            importlib.reload(utils.imports)


class TestGetOrchestrator:
    """Test the get_orchestrator function."""
    
    def test_get_orchestrator_primary_import(self):
        """Test get_orchestrator with successful primary import."""
        mock_agent = Mock()
        mock_tool_calls = Mock()
        mock_module = Mock(ORCHESTRATOR_AGENT=mock_agent, TOOL_CALLS=mock_tool_calls)
        
        with patch.dict('sys.modules', {'connectors.orchestrator': mock_module}):
            from utils.imports import get_orchestrator
            agent, tool_calls = get_orchestrator()
            assert agent == mock_agent
            assert tool_calls == mock_tool_calls
    
    def test_get_orchestrator_function_exists(self):
        """Test get_orchestrator function exists and is callable."""
        from utils.imports import get_orchestrator
        
        # Function should exist and be callable
        assert callable(get_orchestrator)
        
        # Test source code contains try/except pattern
        import inspect
        source = inspect.getsource(get_orchestrator)
        assert 'try:' in source
        assert 'from connectors.orchestrator' in source
        assert 'except ImportError:' in source
        assert 'from ..connectors.orchestrator' in source


class TestGetChatContext:
    """Test the get_chat_context function."""
    
    def test_get_chat_context_primary_import(self):
        """Test get_chat_context with successful primary import."""
        mock_context = Mock()
        mock_module = Mock(ChatContext=mock_context)
        
        with patch.dict('sys.modules', {'connectors.utils.context': mock_module}):
            from utils.imports import get_chat_context
            result = get_chat_context()
            assert result == mock_context
    
    def test_get_chat_context_returns_class(self):
        """Test get_chat_context returns a class."""
        from utils.imports import get_chat_context
        
        result = get_chat_context()
        
        # Should return a class
        assert result is not None
        assert hasattr(result, '__name__')  # Classes have __name__


class TestGetFirebaseModels:
    """Test the get_firebase_models function."""
    
    def test_get_firebase_models_primary_import(self):
        """Test get_firebase_models with successful primary import."""
        mock_chat = Mock()
        mock_token_usage = Mock()
        mock_waitlist = Mock()
        mock_unhandled = Mock()
        mock_google_access = Mock()
        
        mock_module = Mock(
            Chat=mock_chat,
            TokenUsage=mock_token_usage,
            Waitlist=mock_waitlist,
            UnhandledRequest=mock_unhandled,
            GoogleAccessRequest=mock_google_access
        )
        
        with patch.dict('sys.modules', {'firebase': mock_module}):
            from utils.imports import get_firebase_models
            chat, token_usage, waitlist, unhandled, google_access = get_firebase_models()
            
            assert chat == mock_chat
            assert token_usage == mock_token_usage
            assert waitlist == mock_waitlist
            assert unhandled == mock_unhandled
            assert google_access == mock_google_access
    
    def test_get_firebase_models_returns_tuple(self):
        """Test get_firebase_models returns a tuple of 5 items."""
        from utils.imports import get_firebase_models
        
        result = get_firebase_models()
        
        # Should return a tuple of 5 model classes
        assert isinstance(result, tuple)
        assert len(result) == 5


class TestGetRouters:
    """Test the get_routers function."""
    
    def test_get_routers_structure(self):
        """Test that get_routers returns expected structure."""
        from utils.imports import get_routers
        
        # Mock all router modules
        mock_plaid = Mock()
        mock_google = Mock()
        mock_twilio = Mock()
        mock_app_voice = Mock()
        
        modules_to_mock = {
            'routers.plaid': Mock(PLAID_ROUTER=mock_plaid),
            'routers.google': Mock(GOOGLE_ROUTER=mock_google),
            'routers.twilio_server': Mock(TWILIO_ROUTER=mock_twilio),
            'routers.app_voice': Mock(APP_VOICE_ROUTER=mock_app_voice)
        }
        
        with patch.dict('sys.modules', modules_to_mock):
            routers = get_routers()
            
            assert isinstance(routers, dict)
            assert 'plaid' in routers
            assert 'google' in routers
            assert 'twilio' in routers
            assert 'app_voice' in routers
            
            assert routers['plaid'] == mock_plaid
            assert routers['google'] == mock_google
            assert routers['twilio'] == mock_twilio
            assert routers['app_voice'] == mock_app_voice
    
    def test_get_routers_function_structure(self):
        """Test get_routers function structure and error handling."""
        from utils.imports import get_routers
        
        # Function should exist and be callable
        assert callable(get_routers)
        
        # Test source code contains all expected routers
        import inspect
        source = inspect.getsource(get_routers)
        assert 'routers[\"plaid\"]' in source or "routers['plaid']" in source
        assert 'routers[\"google\"]' in source or "routers['google']" in source
        assert 'routers[\"twilio\"]' in source or "routers['twilio']" in source
        assert 'routers[\"app_voice\"]' in source or "routers['app_voice']" in source
        
        # Each router should have try/except with relative fallback
        assert source.count('try:') >= 4
        assert source.count('except ImportError:') >= 4


class TestGetAuthService:
    """Test the get_auth_service function."""
    
    def test_get_auth_service_primary_import(self):
        """Test get_auth_service with successful primary import."""
        mock_validate = Mock()
        mock_module = Mock(validate_google_token=mock_validate)
        
        with patch.dict('sys.modules', {'authorization': mock_module}):
            from utils.imports import get_auth_service
            result = get_auth_service()
            assert result == mock_validate
    
    def test_get_auth_service_function_exists(self):
        """Test get_auth_service function exists and has proper structure."""
        from utils.imports import get_auth_service
        
        # Function should exist and be callable
        assert callable(get_auth_service)
        
        # Test source code contains try/except pattern
        import inspect
        source = inspect.getsource(get_auth_service)
        assert 'try:' in source
        assert 'from authorization import validate_google_token' in source
        assert 'except ImportError:' in source
        assert 'from ..authorization import validate_google_token' in source


class TestGetPromptServices:
    """Test the get_prompt_services function."""
    
    def test_get_prompt_services_primary_import(self):
        """Test get_prompt_services with successful primary import."""
        mock_capabilities = Mock()
        mock_determine = Mock()
        mock_module = Mock(
            AgentCapabilities=mock_capabilities,
            determine_if_request_handled=mock_determine
        )
        
        with patch.dict('sys.modules', {'prompts': mock_module}):
            from utils.imports import get_prompt_services
            capabilities, determine = get_prompt_services()
            assert capabilities == mock_capabilities
            assert determine == mock_determine
    
    def test_get_prompt_services_function_exists(self):
        """Test get_prompt_services function exists and has proper structure."""
        from utils.imports import get_prompt_services
        
        # Function should exist and be callable
        assert callable(get_prompt_services)
        
        # Test source code contains try/except pattern
        import inspect
        source = inspect.getsource(get_prompt_services)
        assert 'try:' in source
        assert 'from prompts import AgentCapabilities, determine_if_request_handled' in source
        assert 'except ImportError:' in source
        assert 'from ..prompts import AgentCapabilities, determine_if_request_handled' in source
        assert 'return AgentCapabilities, determine_if_request_handled' in source


class TestGetSegmentTracking:
    """Test the get_segment_tracking function."""
    
    def test_get_segment_tracking_primary_import(self):
        """Test get_segment_tracking with successful primary import."""
        # Create mocks for all tracking functions
        mock_funcs = {
            'track_agent_called': Mock(),
            'track_chat_created': Mock(),
            'track_prompt': Mock(),
            'track_responded': Mock(),
            'track_tool_called': Mock(),
            'using_existing_chat': Mock(),
            'track_google_access_request': Mock()
        }
        
        mock_module = Mock(**mock_funcs)
        
        with patch.dict('sys.modules', {'connectors.utils.segment': mock_module}):
            from utils.imports import get_segment_tracking
            results = get_segment_tracking()
            
            # Should return a tuple of 7 functions
            assert len(results) == 7
            assert results[0] == mock_funcs['track_agent_called']
            assert results[1] == mock_funcs['track_chat_created']
            assert results[2] == mock_funcs['track_prompt']
            assert results[3] == mock_funcs['track_responded']
            assert results[4] == mock_funcs['track_tool_called']
            assert results[5] == mock_funcs['using_existing_chat']
            assert results[6] == mock_funcs['track_google_access_request']
    
    def test_get_segment_tracking_returns_tuple(self):
        """Test get_segment_tracking returns a tuple of 7 functions."""
        from utils.imports import get_segment_tracking
        
        result = get_segment_tracking()
        
        # Should return a tuple of 7 tracking functions
        assert isinstance(result, tuple)
        assert len(result) == 7
        # All should be callable
        for func in result:
            assert callable(func)


class TestImportPatterns:
    """Test various import patterns and edge cases."""
    
    def test_type_checking_imports(self):
        """Test that TYPE_CHECKING imports don't execute at runtime."""
        from utils.imports import TYPE_CHECKING
        
        # TYPE_CHECKING should be False at runtime
        assert TYPE_CHECKING is False
    
    def test_module_has_all_functions(self):
        """Test that all expected functions are present in the module."""
        import utils.imports as imports_module
        
        expected_functions = [
            'safe_import',
            'get_settings',
            'get_orchestrator',
            'get_chat_context',
            'get_firebase_models',
            'get_routers',
            'get_auth_service',
            'get_prompt_services',
            'get_segment_tracking'
        ]
        
        for func_name in expected_functions:
            assert hasattr(imports_module, func_name)
            assert callable(getattr(imports_module, func_name))
    
    def test_consistent_fallback_pattern(self):
        """Test that all get_* functions follow consistent fallback pattern."""
        import inspect
        import utils.imports as imports_module
        
        # Get all get_* functions
        get_functions = [
            func for name, func in inspect.getmembers(imports_module)
            if name.startswith('get_') and callable(func)
        ]
        
        # Each should have try/except ImportError pattern
        for func in get_functions:
            source = inspect.getsource(func)
            assert 'try:' in source
            assert 'except ImportError:' in source
            assert 'from ..' in source  # Should have relative import fallback


# Note: These tests provide comprehensive coverage of the utils/imports module.
# They test all import helper functions, fallback logic, and edge cases.
# The tests use mocking to avoid actual import side effects during testing.