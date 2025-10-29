from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import datetime
import os.path
import uuid
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from agents import Agent, function_tool, RunContextWrapper
from .utils.responses import ToolResponse
from .utils.context import ChatContext, is_google_enabled
from .utils.google import fetch_google_creds


@function_tool(is_enabled=is_google_enabled)
def save_google_doc(wrapper: RunContextWrapper[ChatContext], title: str, content: str) -> dict:
    """Create Google Doc with title and content.

    Args:
        wrapper: Context with auth
        title: Document name
        content: Text content (supports line breaks)

    Returns:
        ToolResponse with documentId
    """
    creds: Credentials | None = fetch_google_creds(wrapper.context.user_id)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    try:
        service = build('docs', 'v1', credentials=creds)
        doc = service.documents().create(body={'title': title}).execute()
        service.documents().batchUpdate(documentId=doc.get('documentId'), body={'requests': [
            {'insertText': {'text': content, 'location': {'index': '1'}}}]}).execute()
        return ToolResponse(
            response_type="save_google_doc",
            agent_name="Google Docs",
            friendly_name="Saved Doc",
            response=doc,
            display_response=False
        ).to_dict()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {'status': 'error', 'message': 'An error occurred'}


@function_tool(is_enabled=is_google_enabled)
def search_google_docs_by_name_or_content(wrapper: RunContextWrapper[ChatContext], query: str) -> dict:
    """Search Docs/Sheets/Slides by title or content. Case-insensitive partial match.

    Args:
        wrapper: Context with auth
        query: Search term

    Returns:
        ToolResponse with list: id, name, webViewLink, full_text
    """
    creds: Credentials | None = fetch_google_creds(wrapper.context.user_id)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    try:
        if creds:
            query = f"fullText contains '{query}' or name contains '{query}'"
            service = build('drive', 'v3', credentials=creds)
            docs = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
            for doc in docs['files']:
                if 'document' in doc['webViewLink']:
                    doc['full_text'] = doc_text = get_doc_text(
                        doc['id'], creds)
                elif 'spreadsheet' in doc['webViewLink']:
                    doc['full_text'] = read_sheet(doc['id'], creds)
                elif 'presentation' in doc['webViewLink']:
                    doc['full_text'] = get_slide_text(doc['id'], creds)
                else:
                    doc['full_text'] = 'This is not a Google Doc, Google Sheet, or Google Slide Presentation'
        else:
            docs = []
        return ToolResponse(
            response_type="search_google_docs",
            agent_name="Google Docs",
            friendly_name="Searched Docs",
            response=docs,
            display_response=False
        ).to_dict()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {'status': 'error', 'message': 'An error occurred'}


def get_doc_text(doc_id: str, creds: Credentials) -> str:
    docs_service = build('docs', 'v1', credentials=creds)
    try:
        doc = docs_service.documents().get(documentId=doc_id).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return 'An error occurred'
    text = ''
    for element in doc.get('body').get('content', []):
        if 'paragraph' in element:
            for run in element['paragraph'].get('elements', []):
                text += run.get('textRun', {}).get('content', '')
    return text


def read_sheet(spreadsheet_id: str, creds: Credentials) -> dict:
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    sheets = sheet.get(spreadsheetId=spreadsheet_id).execute()
    print(sheets)
    if 'sheets' in sheets:
        sheet_names = [sheet.get('properties', {}).get('title')
                       for sheet in sheets['sheets']]
        print(sheet_names)
        sheet_values = {'sheets': {}}
    else:
        sheet_names = [sheets.get('properties', {}).get('title')]
        sheet_values = {'sheets': {}}
    for sheet_name in sheet_names:
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A1:Z1000'
        ).execute()
        values = result.get('values', [])
        print(values)
        if values:
            sheet_values['sheets'][sheet_name] = values
    return sheet_values


def get_slide_text(presentation_id: str, creds: Credentials) -> str:
    service = build('slides', 'v1', credentials=creds)
    presentation = service.presentations().get(
        presentationId=presentation_id).execute()

    slides = presentation.get('slides', [])
    print(f"Title: {presentation.get('title')}")
    print(f"Total Slides: {len(slides)}")

    full_content = ''
    for i, slide in enumerate(slides):
        print(f"\n--- Slide {i + 1} ---")
        for element in slide.get('pageElements', []):
            if 'shape' in element and 'text' in element['shape']:
                text_content = element['shape']['text'].get('textElements', [])
                for te in text_content:
                    text = te.get('textRun', {}).get('content')
                    if text:
                        print(text.strip())
                        full_content += text.strip() + '\n'

    return full_content


# @function_tool
# def get_google_doc_text(wrapper: RunContextWrapper[ChatContext], doc_id: str):
#     """
#     Gets the text of a Google Doc with the given ID.

#     Args:
#         doc_id (str): The ID of the Google Doc
#     """
#     creds = Credentials.from_authorized_user_file(
#         './auth/credentials/george_odai_creds.json')
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#     return get_doc_text(doc_id, creds)


GOOGLE_DOCS_AGENT = Agent(
    name="Google Docs",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    """Google Workspace assistant. Create Docs with title/content. Search Docs/Sheets/Slides by name or content. Returns full text.""",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Google Docs/Sheets/Slides: create docs, search by title/content.""",
    tools=[save_google_doc, search_google_docs_by_name_or_content],
)

ALL_TOOLS = [save_google_doc, search_google_docs_by_name_or_content]
