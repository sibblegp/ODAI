import base64
import pprint
from email.message import EmailMessage

from agents import Agent, RunContextWrapper, function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from html2text import html2text

from .google_docs import GOOGLE_DOCS_AGENT
from .utils.context import ChatContext, is_google_enabled
# from .easypost import EASYPOST_AGENT
from .utils.google import fetch_google_creds
from .utils.responses import GoogleAccountNeededResponse, ToolResponse

try:
    from firebase import GoogleToken
except ImportError:
    from ..firebase import GoogleToken


def process_email_messages(results: dict, service: 'function') -> list[dict]:
    """
    Process a list of email messages.
    """
    messages = []
    if "messages" in results:
        for message in results["messages"]:
            message_cc = []
            message_bcc = []
            message_html = ""
            message_plain = ""
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=message["id"])
                .execute()
            )
            # pprint.pp(msg['payload']['parts'])
            # print(base64.urlsafe_b64decode(msg['payload']['parts'][1]['body']['data']).decode('utf-8'))
            if "parts" in msg["payload"]:
                print("DECODING MULTIPLE PARTS BODY")
                for part in msg["payload"]["parts"]:
                    if part["mimeType"] == "text/html":
                        message_html = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")

                    elif part["mimeType"] == "text/plain":
                        message_plain = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")
            else:
                try:
                    print("DECODING SINGLE PART BODY")
                    if msg["payload"]["mimeType"] == "text/html":
                        message_html = base64.urlsafe_b64decode(
                            msg["payload"]["body"]["data"]
                        ).decode("utf-8")
                    elif msg["payload"]["mimeType"] == "text/plain":
                        message_plain = base64.urlsafe_b64decode(
                            msg["payload"]["body"]["data"]
                        ).decode("utf-8")
                except KeyError as e:
                    message_html = ""
                    message_plain = ""

            # try:
            #     message_html = base64.urlsafe_b64decode(
            #         msg['payload']['parts'][1]['body']['data']).decode('utf-8')
            # except KeyError:
            #     message_html = base64.urlsafe_b64decode(
            #         msg['payload']['parts'][0]['body']['data']).decode('utf-8')
            # except KeyError:
            #     message_html = ''
            for header in msg["payload"]["headers"]:
                if header["name"] == "Subject":
                    message_subject = header["value"]
                elif header["name"] == "From":
                    message_from = header["value"]
                elif header["name"] == "To":
                    message_to = header["value"]
                elif header["name"] == "Cc":
                    message_cc = header["value"]
                elif header["name"] == "Bcc":
                    message_bcc = header["value"]
                elif header["name"] == "Message-Id":
                    reply_to_id = header["value"]
                    # print(f"reply_to_id: {reply_to_id}")
                elif header["name"] == "Message-ID":
                    reply_to_id = header["value"]
                    # print(f"reply_to_id: {reply_to_id}")
            # print(msg['labelIds'])
            message_unread = "UNREAD" in msg["labelIds"]
            if message_cc and isinstance(message_cc, str):
                message_cc = message_cc.split(",")
            elif isinstance(message_cc, list):
                # Already a list, do nothing
                pass
            else:
                message_cc = []
            if message_bcc and isinstance(message_bcc, str):
                message_bcc = message_bcc.split(",")
            elif isinstance(message_bcc, list):
                # Already a list, do nothing
                pass
            else:
                message_bcc = []
            if message_html:
                message_markdown = html2text(message_html)
                # print(message_markdown)
            else:
                message_markdown = message_plain
            messages.append(
                {
                    "subject": message_subject,
                    "from": message_from,
                    "to": message_to,
                    "markdown": message_markdown,
                    "text": message_plain,
                    "unread": message_unread,
                    "id": message["id"],
                    "thread_id": message["threadId"],
                    "reply_to_id": reply_to_id,
                    "cc": message_cc,
                    "bcc": message_bcc,
                }
            )
    return messages


@function_tool(is_enabled=is_google_enabled)
def fetch_google_email_inbox(
    wrapper: RunContextWrapper[ChatContext], unread: bool = False
) -> dict:
    """Fetch recent Gmail inbox emails (max 10).

    Args:
        wrapper: Context with auth
        unread: Only unread emails if True

    Returns:
        ToolResponse with email list: subject, from, to, markdown body, id, thread_id
    """
    creds: Credentials | None = fetch_google_creds(wrapper.context.user_id)
    # Credentials.from_authorized_user_info
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save the credentials for the next run
            with open("./auth/credentials/george_odai_creds.json", "w") as token:
                token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        if unread:
            results = (
                service.users()
                .messages()
                .list(userId="me", q="label:INBOX label:UNREAD", maxResults=10)
                .execute()
            )
        else:
            results = (
                service.users()
                .messages()
                .list(userId="me", q="label:INBOX", maxResults=10)
                .execute()
            )
        messages = process_email_messages(results, service)
        # print(messages)
        # print(results)
        return ToolResponse(
            response_type="google_email_inbox",
            agent_name="GMail",
            friendly_name="GMAIL Inbox",
            response=messages,
        ).to_dict()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {"status": "error", "message": "An error occurred"}


@function_tool(is_enabled=is_google_enabled)
def search_google_mail(wrapper: RunContextWrapper[ChatContext], query: str) -> dict:
    """Search Gmail with query syntax (from:, subject:, has:attachment, etc).

    Args:
        wrapper: Context with auth
        query: Gmail search query

    Returns:
        ToolResponse with matching emails
    """
    creds: Credentials | None = fetch_google_creds(wrapper.context.user_id)
    # Credentials.from_authorized_user_info
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save the credentials for the next run
            # with open("./auth/credentials/george_odai_creds.json", "w") as token:
            #     token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = process_email_messages(results, service)
        return ToolResponse(
            response_type="google_email_search",
            agent_name="GMail",
            friendly_name="GMAIL Inbox",
            response=messages,
        ).to_dict()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {"status": "error", "message": "An error occurred"}


@function_tool(is_enabled=is_google_enabled)
def search_google_mail_from_email(wrapper: RunContextWrapper[ChatContext], email: str) -> dict:
    """Search all emails from specific sender.

    Args:
        wrapper: Context with auth
        email: Sender's email address

    Returns:
        ToolResponse with emails from that sender
    """
    creds: Credentials | None = fetch_google_creds(wrapper.context.user_id)
    # Credentials.from_authorized_user_info
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save the credentials for the next run
            # with open("./auth/credentials/george_odai_creds.json", "w") as token:
            #     token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        query = f"from:{email}"
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = process_email_messages(results, service)
        return ToolResponse(
            response_type="google_email_search_from_email",
            agent_name="GMail",
            friendly_name="GMAIL Inbox from " + email,
            response=messages,
        ).to_dict()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {"status": "error", "message": "An error occurred"}


@function_tool(is_enabled=is_google_enabled)
def send_google_email(
    wrapper: RunContextWrapper[ChatContext],
    sender_name: str,
    sender_email: str,
    recipient_email_addresses: list[str],
    cc: list[str],
    bcc: list[str],
    subject: str,
    body: str,
) -> dict:
    """Send email via Gmail. ONLY when user explicitly says "send".

    Args:
        wrapper: Context with auth
        sender_name: Display name
        sender_email: Must match Gmail account
        recipient_email_addresses: To recipients (required)
        cc/bcc: CC/BCC lists
        subject: Email subject
        body: Plain text content

    Returns:
        ToolResponse with sent email details
    """
    creds = fetch_google_creds(wrapper.context.user_id)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save the credentials for the next run
            with open("./auth/credentials/george_odai_creds.json", "w") as token:
                token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = ", ".join(recipient_email_addresses)
        message["cc"] = ", ".join(cc)
        message["bcc"] = ", ".join(bcc)
        message["Subject"] = subject
        message.set_content(body)
        encoded_message = base64.urlsafe_b64encode(
            message.as_bytes()).decode("utf-8")
        service.users().messages().send(
            userId="me", body={"raw": encoded_message}
        ).execute()
        return ToolResponse(
            response_type="send_google_email",
            agent_name="GMail",
            friendly_name="Sent Email",
            response={
                "to": recipient_email_addresses,
                "cc": cc,
                "bcc": bcc,
                "subject": subject,
                "body": body,
            },
        ).to_dict()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {"status": "error", "message": "An error occurred"}


@function_tool(is_enabled=is_google_enabled)
def reply_to_google_email(
    wrapper: RunContextWrapper[ChatContext],
    sender_name: str,
    sender_email: str,
    to: list[str],
    cc: list[str],
    bcc: list[str],
    subject: str,
    reply_to_id: str,
    thread_id: str,
    body: str,
) -> dict:
    """Reply to email thread maintaining conversation.

    Args:
        wrapper: Context with auth
        sender_name/email: Sender info
        to/cc/bcc: Recipients
        subject: Usually "Re: " + original
        reply_to_id: Original message ID
        thread_id: Gmail thread ID
        body: Reply content

    Returns:
        ToolResponse with sent reply details
    """
    creds: Credentials | None = fetch_google_creds(wrapper.context.user_id)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    # Save the credentials for the next run
    # print(f'reply_to_id: {reply_to_id}')
    # print(f'thread_id: {thread_id}')
    # print(f'sender_name: {sender_name}')
    # print(f'sender_email: {sender_email}')
    # print(f'to: {to}')
    # print(f'cc: {cc}')
    # print(f'bcc: {bcc}')
    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = ", ".join(to)
        message["cc"] = ", ".join(cc)
        message["bcc"] = ", ".join(bcc)
        message["In-Reply-To"] = reply_to_id
        message["References"] = reply_to_id
        message["Subject"] = f"{subject}"
        message.set_content(body)
        encoded_message = base64.urlsafe_b64encode(
            message.as_bytes()).decode("utf-8")
        created_message = {
            "raw": encoded_message,
            "threadId": thread_id,
        }
        # print(created_message)
        service.users().messages().send(userId="me", body=created_message).execute()
        return ToolResponse(
            response_type="reply_to_google_email",
            agent_name="GMail",
            friendly_name="Replied to Email",
            response={"to": to, "cc": cc, "bcc": bcc,
                      "subject": subject, "body": body},
        ).to_dict()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return {"status": "error", "message": "An error occurred"}


GMAIL_AGENT = Agent(
    name="GMail",
    model="gpt-4o",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    """Gmail assistant. Search (from:, subject:, has:attachment), send emails (ONLY when user says "send"), reply to threads, view inbox. Max 10 emails per fetch. No attachments.""",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Gmail: search, send (only on request), reply, view inbox. Supports Gmail query syntax.""",
    tools=[
        search_google_mail,
        send_google_email,
        reply_to_google_email,
        fetch_google_email_inbox,
        search_google_mail_from_email,
    ],
    handoffs=[GOOGLE_DOCS_AGENT],
)

ALL_TOOLS = [search_google_mail, send_google_email, reply_to_google_email,
             fetch_google_email_inbox, search_google_mail_from_email]
