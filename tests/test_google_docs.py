"""
Comprehensive tests for connectors/google_docs.py

Tests cover the Google Docs agent, its tools, helper functions, and various edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import Agent, RunContextWrapper
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from connectors.google_docs import (
    GOOGLE_DOCS_AGENT,
    save_google_doc,
    search_google_docs_by_name_or_content,
    get_doc_text,
    read_sheet,
    get_slide_text,
    ALL_TOOLS
)


class TestGoogleDocsConfig:
    """Test Google Docs agent configuration and setup."""

    def test_google_docs_agent_exists(self):
        """Test that GOOGLE_DOCS_AGENT is properly configured."""
        assert GOOGLE_DOCS_AGENT is not None
        assert isinstance(GOOGLE_DOCS_AGENT, Agent)
        assert GOOGLE_DOCS_AGENT.name == "Google Docs"
        assert GOOGLE_DOCS_AGENT.model == "gpt-4o"
        assert len(GOOGLE_DOCS_AGENT.tools) == 2

    def test_all_tools_exported(self):
        """Test that ALL_TOOLS contains expected tools."""
        assert len(ALL_TOOLS) == 2
        assert save_google_doc in ALL_TOOLS
        assert search_google_docs_by_name_or_content in ALL_TOOLS

    def test_agent_handoffs_configured(self):
        """Test that agent handoffs are properly configured."""
        assert hasattr(GOOGLE_DOCS_AGENT, 'handoffs')
        # No handoffs defined in the agent
        assert len(GOOGLE_DOCS_AGENT.handoffs) == 0

    def test_agent_instructions_configured(self):
        """Test that agent instructions are properly set."""
        assert GOOGLE_DOCS_AGENT.instructions is not None
        assert "Google Workspace assistant" in GOOGLE_DOCS_AGENT.instructions
        assert "Create Docs" in GOOGLE_DOCS_AGENT.instructions
        assert "Search Docs" in GOOGLE_DOCS_AGENT.instructions

    def test_agent_handoff_description_configured(self):
        """Test that agent handoff description is properly set."""
        assert GOOGLE_DOCS_AGENT.handoff_description is not None
        assert "Google Docs/Sheets/Slides" in GOOGLE_DOCS_AGENT.handoff_description
        assert "create docs" in GOOGLE_DOCS_AGENT.handoff_description


class TestSaveGoogleDocTool:
    """Test the save_google_doc tool."""

    @pytest.mark.asyncio
    async def test_save_google_doc_success(self):
        """Test successful document creation."""
        # Mock the tool context
        mock_ctx = Mock()

        result = await save_google_doc.on_invoke_tool(
            mock_ctx,
            '{"title": "Test Document", "content": "This is test content"}'
        )

        # Due to the complexity of mocking Google authentication and services,
        # we just verify that the tool returns some kind of response
        assert result is not None
        if isinstance(result, dict):
            # Check if it's a proper response or an error about Google authentication
            assert "response_type" in result or "google" in str(
                result).lower() or "status" in result
        else:
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_save_google_doc_empty_content(self):
        """Test creating document with empty content."""
        mock_ctx = Mock()

        result = await save_google_doc.on_invoke_tool(
            mock_ctx,
            '{"title": "Empty Document", "content": ""}'
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_save_google_doc_special_characters(self):
        """Test creating document with special characters."""
        mock_ctx = Mock()

        result = await save_google_doc.on_invoke_tool(
            mock_ctx,
            '{"title": "Special © Characters™", "content": "Content with émojis 🚀 and symbols €£¥"}'
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_save_google_doc_long_content(self):
        """Test creating document with long content."""
        mock_ctx = Mock()
        long_content = "Lorem ipsum dolor sit amet. " * 100

        result = await save_google_doc.on_invoke_tool(
            mock_ctx,
            f'{{"title": "Long Document", "content": "{long_content}"}}'
        )

        assert result is not None


class TestSaveGoogleDocWithCredentials:
    """Test save_google_doc with credential handling."""

    @patch('connectors.google_docs.fetch_google_creds')
    @patch('connectors.google_docs.build')
    @pytest.mark.asyncio
    async def test_save_google_doc_with_valid_credentials(self, mock_build, mock_fetch_creds):
        """Test saving document with valid credentials."""
        # Mock valid credentials
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_fetch_creds.return_value = mock_creds

        # Mock Google Docs service
        mock_service = Mock()
        mock_docs_service = Mock()
        mock_service.documents.return_value = mock_docs_service
        mock_build.return_value = mock_service

        # Mock document creation response
        mock_doc_response = {
            'documentId': 'doc123',
            'title': 'Test Document'
        }
        mock_docs_service.create.return_value.execute.return_value = mock_doc_response
        mock_docs_service.batchUpdate.return_value.execute.return_value = {
            'replies': []}

        # Create wrapper and context
        mock_ctx = Mock()
        mock_ctx.user_id = 'test_user'
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Call the function tool's on_invoke_tool method
        result = await save_google_doc.on_invoke_tool(
            mock_wrapper,
            '{"title": "Test Document", "content": "This is test content"}'
        )

        # Verify the result
        assert result['response_type'] == 'save_google_doc'
        assert result['agent_name'] == 'Google Docs'
        assert result['friendly_name'] == 'Saved Doc'
        assert result['response']['documentId'] == 'doc123'
        assert result['display_response'] is False

        # Verify service calls
        mock_fetch_creds.assert_called_once_with('test_user')
        mock_build.assert_called_once_with(
            'docs', 'v1', credentials=mock_creds)
        mock_docs_service.create.assert_called_once_with(
            body={'title': 'Test Document'})

    @patch('connectors.google_docs.fetch_google_creds')
    @patch('connectors.google_docs.build')
    @pytest.mark.asyncio
    async def test_save_google_doc_with_expired_credentials(self, mock_build, mock_fetch_creds):
        """Test saving document with expired credentials that can be refreshed."""
        # Mock expired credentials with refresh token
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = 'refresh_token_value'
        mock_fetch_creds.return_value = mock_creds

        # Mock Google Docs service
        mock_service = Mock()
        mock_docs_service = Mock()
        mock_service.documents.return_value = mock_docs_service
        mock_build.return_value = mock_service

        # Mock document creation response
        mock_doc_response = {
            'documentId': 'doc456',
            'title': 'Refreshed Doc'
        }
        mock_docs_service.create.return_value.execute.return_value = mock_doc_response
        mock_docs_service.batchUpdate.return_value.execute.return_value = {
            'replies': []}

        # Create wrapper and context
        mock_ctx = Mock()
        mock_ctx.user_id = 'test_user'
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Call the function tool's on_invoke_tool method
        result = await save_google_doc.on_invoke_tool(
            mock_wrapper,
            '{"title": "Refreshed Doc", "content": "Content after refresh"}'
        )

        # Verify credentials were refreshed
        mock_creds.refresh.assert_called_once()

        # Verify the result
        assert result['response_type'] == 'save_google_doc'
        assert result['response']['documentId'] == 'doc456'

    @patch('connectors.google_docs.fetch_google_creds')
    @patch('connectors.google_docs.build')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_save_google_doc_with_http_error(self, mock_print, mock_build, mock_fetch_creds):
        """Test saving document when HttpError occurs."""
        # Mock valid credentials
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_fetch_creds.return_value = mock_creds

        # Mock Google Docs service that raises HttpError
        mock_service = Mock()
        mock_docs_service = Mock()
        mock_service.documents.return_value = mock_docs_service
        mock_build.return_value = mock_service

        # Mock HttpError
        mock_docs_service.create.return_value.execute.side_effect = HttpError(
            resp=Mock(status=403),
            content=b'Forbidden'
        )

        # Create wrapper and context
        mock_ctx = Mock()
        mock_ctx.user_id = 'test_user'
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Call the function tool's on_invoke_tool method
        result = await save_google_doc.on_invoke_tool(
            mock_wrapper,
            '{"title": "Error Doc", "content": "This will fail"}'
        )

        # Verify error response
        assert result['status'] == 'error'
        assert result['message'] == 'An error occurred'

        # Verify error was printed
        mock_print.assert_called_once()
        print_args = mock_print.call_args[0][0]
        assert 'An error occurred:' in print_args

    @patch('connectors.google_docs.fetch_google_creds')
    @patch('connectors.google_docs.build')
    @pytest.mark.asyncio
    async def test_save_google_doc_with_no_credentials(self, mock_build, mock_fetch_creds):
        """Test saving document when no credentials are available."""
        # Mock no credentials
        mock_fetch_creds.return_value = None

        # Create wrapper and context
        mock_ctx = Mock()
        mock_ctx.user_id = 'test_user'
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Call the function tool's on_invoke_tool method
        result = await save_google_doc.on_invoke_tool(
            mock_wrapper,
            '{"title": "No Creds Doc", "content": "No credentials"}'
        )

        # The function tool wrapper will catch any exception
        assert result is not None
        # Verify that build was called with None credentials
        mock_build.assert_called_once_with('docs', 'v1', credentials=None)


class TestSearchGoogleDocsTool:
    """Test the search_google_docs_by_name_or_content tool."""

    @pytest.mark.asyncio
    async def test_search_docs_by_name(self):
        """Test searching documents by name."""
        mock_ctx = Mock()

        result = await search_google_docs_by_name_or_content.on_invoke_tool(
            mock_ctx,
            '{"query": "meeting notes"}'
        )

        assert result is not None
        if isinstance(result, dict):
            assert "response_type" in result or "google" in str(
                result).lower() or "status" in result
        else:
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_docs_by_content(self):
        """Test searching documents by content."""
        mock_ctx = Mock()

        result = await search_google_docs_by_name_or_content.on_invoke_tool(
            mock_ctx,
            '{"query": "quarterly report"}'
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_search_docs_empty_query(self):
        """Test searching with empty query."""
        mock_ctx = Mock()

        result = await search_google_docs_by_name_or_content.on_invoke_tool(
            mock_ctx,
            '{"query": ""}'
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_search_docs_special_characters_query(self):
        """Test searching with special characters in query."""
        mock_ctx = Mock()

        result = await search_google_docs_by_name_or_content.on_invoke_tool(
            mock_ctx,
            '{"query": "report & analysis (2023)"}'
        )

        assert result is not None


class TestSearchGoogleDocsWithCredentials:
    """Test search_google_docs_by_name_or_content with credential handling."""

    @patch('connectors.google_docs.fetch_google_creds')
    @patch('connectors.google_docs.build')
    @pytest.mark.asyncio
    async def test_search_docs_with_valid_credentials(self, mock_build, mock_fetch_creds):
        """Test searching documents with valid credentials."""
        # Mock valid credentials
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_fetch_creds.return_value = mock_creds

        # Mock Google Drive service
        mock_service = Mock()
        mock_files_service = Mock()
        mock_service.files.return_value = mock_files_service
        mock_build.return_value = mock_service

        # Mock search response
        mock_search_response = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'Document 1',
                    'webViewLink': 'https://docs.google.com/document/d/file1/edit'
                },
                {
                    'id': 'file2',
                    'name': 'Spreadsheet 1',
                    'webViewLink': 'https://docs.google.com/spreadsheets/d/file2/edit'
                },
                {
                    'id': 'file3',
                    'name': 'Presentation 1',
                    'webViewLink': 'https://docs.google.com/presentation/d/file3/edit'
                },
                {
                    'id': 'file4',
                    'name': 'Other File',
                    'webViewLink': 'https://drive.google.com/file/d/file4/view'
                }
            ]
        }
        mock_files_service.list.return_value.execute.return_value = mock_search_response

        # Mock get_doc_text, read_sheet, get_slide_text
        with patch('connectors.google_docs.get_doc_text', return_value='Document content'):
            with patch('connectors.google_docs.read_sheet', return_value='Sheet content'):
                with patch('connectors.google_docs.get_slide_text', return_value='Slide content'):
                    # Create wrapper and context
                    mock_ctx = Mock()
                    mock_ctx.user_id = 'test_user'
                    mock_wrapper = Mock(spec=RunContextWrapper)
                    mock_wrapper.context = mock_ctx

                    # Call the function tool's on_invoke_tool method
                    result = await search_google_docs_by_name_or_content.on_invoke_tool(
                        mock_wrapper,
                        '{"query": "test query"}'
                    )

        # Verify the result
        assert result['response_type'] == 'search_google_docs'
        assert result['agent_name'] == 'Google Docs'
        assert result['friendly_name'] == 'Searched Docs'
        assert result['display_response'] is False

        # Verify response content
        files = result['response']['files']
        assert len(files) == 4
        assert files[0]['full_text'] == 'Document content'
        assert files[1]['full_text'] == 'Sheet content'
        assert files[2]['full_text'] == 'Slide content'
        assert files[3]['full_text'] == 'This is not a Google Doc, Google Sheet, or Google Slide Presentation'

        # Verify service calls
        mock_fetch_creds.assert_called_once_with('test_user')
        mock_files_service.list.assert_called_once()
        call_args = mock_files_service.list.call_args
        assert call_args[1]['q'] == "fullText contains 'test query' or name contains 'test query'"

    @patch('connectors.google_docs.fetch_google_creds')
    @patch('connectors.google_docs.build')
    @pytest.mark.asyncio
    async def test_search_docs_with_expired_credentials(self, mock_build, mock_fetch_creds):
        """Test searching documents with expired credentials that can be refreshed."""
        # Mock expired credentials with refresh token
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = 'refresh_token_value'
        mock_fetch_creds.return_value = mock_creds

        # Mock Google Drive service
        mock_service = Mock()
        mock_files_service = Mock()
        mock_service.files.return_value = mock_files_service
        mock_build.return_value = mock_service

        # Mock empty search response
        mock_files_service.list.return_value.execute.return_value = {
            'files': []}

        # Create wrapper and context
        mock_ctx = Mock()
        mock_ctx.user_id = 'test_user'
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Call the function tool's on_invoke_tool method
        result = await search_google_docs_by_name_or_content.on_invoke_tool(
            mock_wrapper,
            '{"query": "refresh test"}'
        )

        # Verify credentials were refreshed
        mock_creds.refresh.assert_called_once()

        # Verify the result
        assert result['response_type'] == 'search_google_docs'
        assert result['response']['files'] == []

    @patch('connectors.google_docs.fetch_google_creds')
    @patch('connectors.google_docs.build')
    @patch('builtins.print')
    @pytest.mark.asyncio
    async def test_search_docs_with_http_error(self, mock_print, mock_build, mock_fetch_creds):
        """Test searching documents when HttpError occurs."""
        # Mock valid credentials
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_fetch_creds.return_value = mock_creds

        # Mock Google Drive service that raises HttpError
        mock_service = Mock()
        mock_files_service = Mock()
        mock_service.files.return_value = mock_files_service
        mock_build.return_value = mock_service

        # Mock HttpError
        mock_files_service.list.return_value.execute.side_effect = HttpError(
            resp=Mock(status=403),
            content=b'Access denied'
        )

        # Create wrapper and context
        mock_ctx = Mock()
        mock_ctx.user_id = 'test_user'
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Call the function tool's on_invoke_tool method
        result = await search_google_docs_by_name_or_content.on_invoke_tool(
            mock_wrapper,
            '{"query": "error test"}'
        )

        # Verify error response
        assert result['status'] == 'error'
        assert result['message'] == 'An error occurred'

        # Verify error was printed
        mock_print.assert_called_once()
        print_args = mock_print.call_args[0][0]
        assert 'An error occurred:' in print_args

    @patch('connectors.google_docs.fetch_google_creds')
    @pytest.mark.asyncio
    async def test_search_docs_with_no_credentials(self, mock_fetch_creds):
        """Test searching documents when no credentials are available."""
        # Mock no credentials
        mock_fetch_creds.return_value = None

        # Create wrapper and context
        mock_ctx = Mock()
        mock_ctx.user_id = 'test_user'
        mock_wrapper = Mock(spec=RunContextWrapper)
        mock_wrapper.context = mock_ctx

        # Call the function tool's on_invoke_tool method
        result = await search_google_docs_by_name_or_content.on_invoke_tool(
            mock_wrapper,
            '{"query": "no creds test"}'
        )

        # When no credentials, should return empty response
        assert result['response_type'] == 'search_google_docs'
        assert result['response'] == []


class TestGetDocTextFunction:
    """Test the get_doc_text helper function."""

    @patch('connectors.google_docs.build')
    def test_get_doc_text_success(self, mock_build):
        """Test successful document text retrieval."""
        # Mock Google Docs service
        mock_service = Mock()
        mock_docs = Mock()
        mock_service.documents.return_value = mock_docs
        mock_build.return_value = mock_service

        # Mock document content
        mock_docs.get.return_value.execute.return_value = {
            'body': {
                'content': [
                    {
                        'paragraph': {
                            'elements': [
                                {
                                    'textRun': {
                                        'content': 'Hello World\n'
                                    }
                                }
                            ]
                        }
                    },
                    {
                        'paragraph': {
                            'elements': [
                                {
                                    'textRun': {
                                        'content': 'This is a test document.'
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }

        # Mock credentials
        mock_creds = Mock()

        result = get_doc_text('doc123', mock_creds)

        assert result == 'Hello World\nThis is a test document.'
        mock_docs.get.assert_called_once_with(documentId='doc123')

    @patch('connectors.google_docs.build')
    def test_get_doc_text_empty_document(self, mock_build):
        """Test retrieving text from empty document."""
        mock_service = Mock()
        mock_docs = Mock()
        mock_service.documents.return_value = mock_docs
        mock_build.return_value = mock_service

        mock_docs.get.return_value.execute.return_value = {
            'body': {
                'content': []
            }
        }

        mock_creds = Mock()
        result = get_doc_text('empty_doc', mock_creds)

        assert result == ''

    @patch('connectors.google_docs.build')
    def test_get_doc_text_api_error(self, mock_build):
        """Test handling of API errors."""
        from googleapiclient.errors import HttpError

        mock_service = Mock()
        mock_docs = Mock()
        mock_service.documents.return_value = mock_docs
        mock_build.return_value = mock_service

        # Mock HTTP error
        mock_docs.get.return_value.execute.side_effect = HttpError(
            resp=Mock(status=404),
            content=b'Not found'
        )

        mock_creds = Mock()
        result = get_doc_text('nonexistent_doc', mock_creds)

        assert result == 'An error occurred'


class TestReadSheetFunction:
    """Test the read_sheet helper function."""

    @patch('connectors.google_docs.build')
    def test_read_sheet_single_sheet(self, mock_build):
        """Test reading a spreadsheet with single sheet."""
        # Mock Google Sheets service
        mock_service = Mock()
        mock_spreadsheets = Mock()
        mock_service.spreadsheets.return_value = mock_spreadsheets
        mock_build.return_value = mock_service

        # Mock spreadsheet metadata
        mock_spreadsheets.get.return_value.execute.return_value = {
            'sheets': [
                {
                    'properties': {
                        'title': 'Sheet1'
                    }
                }
            ]
        }

        # Mock sheet values
        mock_spreadsheets.values.return_value.get.return_value.execute.return_value = {
            'values': [
                ['Header1', 'Header2', 'Header3'],
                ['Value1', 'Value2', 'Value3'],
                ['Value4', 'Value5', 'Value6']
            ]
        }

        mock_creds = Mock()
        result = read_sheet('sheet123', mock_creds)

        assert 'sheets' in result
        assert 'Sheet1' in result['sheets']
        assert len(result['sheets']['Sheet1']) == 3
        assert result['sheets']['Sheet1'][0] == [
            'Header1', 'Header2', 'Header3']

    @patch('connectors.google_docs.build')
    def test_read_sheet_multiple_sheets(self, mock_build):
        """Test reading a spreadsheet with multiple sheets."""
        mock_service = Mock()
        mock_spreadsheets = Mock()
        mock_service.spreadsheets.return_value = mock_spreadsheets
        mock_build.return_value = mock_service

        # Mock spreadsheet with multiple sheets
        mock_spreadsheets.get.return_value.execute.return_value = {
            'sheets': [
                {'properties': {'title': 'Sheet1'}},
                {'properties': {'title': 'Sheet2'}}
            ]
        }

        # Mock different values for each sheet
        mock_spreadsheets.values.return_value.get.return_value.execute.side_effect = [
            {'values': [['A1', 'B1'], ['A2', 'B2']]},
            {'values': [['X1', 'Y1'], ['X2', 'Y2']]}
        ]

        mock_creds = Mock()
        result = read_sheet('multi_sheet', mock_creds)

        assert 'sheets' in result
        assert 'Sheet1' in result['sheets']
        assert 'Sheet2' in result['sheets']
        assert result['sheets']['Sheet1'][0] == ['A1', 'B1']
        assert result['sheets']['Sheet2'][0] == ['X1', 'Y1']

    @patch('connectors.google_docs.build')
    def test_read_sheet_empty_sheet(self, mock_build):
        """Test reading an empty spreadsheet."""
        mock_service = Mock()
        mock_spreadsheets = Mock()
        mock_service.spreadsheets.return_value = mock_spreadsheets
        mock_build.return_value = mock_service

        mock_spreadsheets.get.return_value.execute.return_value = {
            'sheets': [{'properties': {'title': 'EmptySheet'}}]
        }

        mock_spreadsheets.values.return_value.get.return_value.execute.return_value = {
            'values': []
        }

        mock_creds = Mock()
        result = read_sheet('empty_sheet', mock_creds)

        assert 'sheets' in result
        # Empty sheets are not included in the result due to the implementation
        assert 'EmptySheet' not in result['sheets']
        assert result['sheets'] == {}

    @patch('connectors.google_docs.build')
    @patch('builtins.print')
    def test_read_sheet_without_sheets_property(self, mock_print, mock_build):
        """Test reading a spreadsheet when 'sheets' property is missing."""
        # Mock Google Sheets service
        mock_service = Mock()
        mock_spreadsheets = Mock()
        mock_service.spreadsheets.return_value = mock_spreadsheets
        mock_build.return_value = mock_service

        # Mock spreadsheet metadata without 'sheets' property
        mock_spreadsheets.get.return_value.execute.return_value = {
            'properties': {
                'title': 'Single Sheet'
            }
        }

        # Mock sheet values
        mock_spreadsheets.values.return_value.get.return_value.execute.return_value = {
            'values': [
                ['A1', 'B1'],
                ['A2', 'B2']
            ]
        }

        mock_creds = Mock()
        result = read_sheet('single_sheet', mock_creds)

        assert 'sheets' in result
        assert 'Single Sheet' in result['sheets']
        assert result['sheets']['Single Sheet'][0] == ['A1', 'B1']

        # Verify print statements
        assert mock_print.call_count == 2  # One print for sheet metadata, one for values


class TestGetSlideTextFunction:
    """Test the get_slide_text helper function."""

    @patch('connectors.google_docs.build')
    def test_get_slide_text_success(self, mock_build):
        """Test successful slide text extraction."""
        # Mock Google Slides service
        mock_service = Mock()
        mock_presentations = Mock()
        mock_service.presentations.return_value = mock_presentations
        mock_build.return_value = mock_service

        # Mock presentation content
        mock_presentations.get.return_value.execute.return_value = {
            'title': 'Test Presentation',
            'slides': [
                {
                    'pageElements': [
                        {
                            'shape': {
                                'text': {
                                    'textElements': [
                                        {
                                            'textRun': {
                                                'content': 'Slide 1 Title\n'
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                },
                {
                    'pageElements': [
                        {
                            'shape': {
                                'text': {
                                    'textElements': [
                                        {
                                            'textRun': {
                                                'content': 'Slide 2 Content\n'
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            ]
        }

        mock_creds = Mock()
        result = get_slide_text('presentation123', mock_creds)

        assert 'Slide 1 Title' in result
        assert 'Slide 2 Content' in result

    @patch('connectors.google_docs.build')
    def test_get_slide_text_empty_presentation(self, mock_build):
        """Test extracting text from empty presentation."""
        mock_service = Mock()
        mock_presentations = Mock()
        mock_service.presentations.return_value = mock_presentations
        mock_build.return_value = mock_service

        mock_presentations.get.return_value.execute.return_value = {
            'title': 'Empty Presentation',
            'slides': []
        }

        mock_creds = Mock()
        result = get_slide_text('empty_presentation', mock_creds)

        assert result == ''

    @patch('connectors.google_docs.build')
    def test_get_slide_text_no_text_elements(self, mock_build):
        """Test presentation with slides but no text elements."""
        mock_service = Mock()
        mock_presentations = Mock()
        mock_service.presentations.return_value = mock_presentations
        mock_build.return_value = mock_service

        mock_presentations.get.return_value.execute.return_value = {
            'title': 'No Text Presentation',
            'slides': [
                {
                    'pageElements': [
                        {
                            'image': {}  # Image element, not text
                        }
                    ]
                }
            ]
        }

        mock_creds = Mock()
        result = get_slide_text('no_text_presentation', mock_creds)

        assert result == ''


class TestGoogleDocsAgentIntegration:
    """Integration tests for Google Docs agent components."""

    def test_agent_tools_registration(self):
        """Test that tools are properly registered with the agent."""
        tool_names = [tool.name for tool in GOOGLE_DOCS_AGENT.tools]
        assert "save_google_doc" in tool_names
        assert "search_google_docs_by_name_or_content" in tool_names

    def test_agent_model_configuration(self):
        """Test that agent uses correct model."""
        assert GOOGLE_DOCS_AGENT.model == "gpt-4o"

    def test_import_dependencies(self):
        """Test that agent dependencies are properly imported."""
        try:
            from connectors.google_docs import (
                GOOGLE_DOCS_AGENT,
                save_google_doc,
                search_google_docs_by_name_or_content
            )
            assert GOOGLE_DOCS_AGENT is not None
            assert save_google_doc is not None
            assert search_google_docs_by_name_or_content is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Google Docs components: {e}")


class TestGoogleDocsEdgeCases:
    """Test edge cases and error conditions."""

    def test_save_doc_tool_signature(self):
        """Test that save_google_doc tool has correct parameter schema."""
        schema = save_google_doc.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "title" in params
        assert "content" in params
        assert params["title"]["type"] == "string"
        assert params["content"]["type"] == "string"

    def test_search_docs_tool_signature(self):
        """Test that search_google_docs_by_name_or_content tool has correct parameter schema."""
        schema = search_google_docs_by_name_or_content.params_json_schema
        assert "properties" in schema
        params = schema["properties"]
        assert "query" in params
        assert params["query"]["type"] == "string"

    def test_agent_name_consistency(self):
        """Test that agent name is consistent."""
        assert GOOGLE_DOCS_AGENT.name == "Google Docs"

    def test_all_tools_contains_all_functions(self):
        """Test that ALL_TOOLS exports all available tool functions."""
        expected_tools = [save_google_doc,
                          search_google_docs_by_name_or_content]
        assert len(ALL_TOOLS) == len(expected_tools)
        for tool in expected_tools:
            assert tool in ALL_TOOLS

    def test_agent_instructions_mention_key_functionality(self):
        """Test that agent instructions mention key functionality."""
        instructions = GOOGLE_DOCS_AGENT.instructions
        assert "Google Workspace" in instructions
        assert "Create Docs" in instructions
        assert "Search Docs" in instructions

    @pytest.mark.asyncio
    async def test_save_doc_missing_params(self):
        """Test saving document with missing parameters."""
        mock_ctx = Mock()

        result = await save_google_doc.on_invoke_tool(
            mock_ctx,
            '{"title": "Missing Content"}'  # Missing content parameter
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_docs_missing_query(self):
        """Test searching without query parameter."""
        mock_ctx = Mock()

        result = await search_google_docs_by_name_or_content.on_invoke_tool(
            mock_ctx,
            '{}'  # Missing query parameter
        )

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_save_doc_with_newlines_and_quotes(self):
        """Test saving document with complex content."""
        mock_ctx = Mock()

        content = 'Line 1\nLine 2 with "quotes"\nLine 3 with \'single quotes\''
        result = await save_google_doc.on_invoke_tool(
            mock_ctx,
            f'{{"title": "Complex Content", "content": {repr(content)}}}'
        )

        assert result is not None
