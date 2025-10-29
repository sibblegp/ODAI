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
from .google_docs import GOOGLE_DOCS_AGENT
from .utils.google import fetch_google_creds


@function_tool(is_enabled=is_google_enabled)
def get_google_calendar_events(wrapper: RunContextWrapper[ChatContext], limit: int = 10, date: str | None = None) -> dict:
    """Get upcoming Google Calendar events.

    Args:
        wrapper: Context with user auth
        limit: Max events to return (default 10, max 250)
        date: Not implemented

    Returns:
        ToolResponse with event list: id, summary, start/end times, attendees, location, Meet link
    """
    creds: Credentials | None = fetch_google_creds(wrapper.context.user_id)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    try:
        service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
        # if not date:
        from_date = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        # else:
        #     from_date = datetime.datetime.strptime(date, "%Y-%m-%d").isoformat()
        #     from_date = from_date.replace(tzinfo=datetime.timezone.utc)
        print(from_date)
        print("Getting the upcoming 10 events")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=from_date,
                maxResults=limit,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return ToolResponse(
                response_type="google_calendar_events",
                agent_name="Google Calendar",
                friendly_name="Google Calendar",
                response="No upcoming events found.",
            ).to_dict()

        # Prints the start and name of the next 10 events
        # for event in events:
        #     start = event["start"].get("dateTime", event["start"].get("date"))
            # print(start, event["summary"])
        return ToolResponse(
            response_type="google_calendar_events",
            agent_name="Google Calendar",
            friendly_name="Google Calendar",
            response=events,
        ).to_dict()

    except HttpError as error:
        print(f"An error occurred: {error}")
        return ToolResponse(
            response_type="google_calendar_events",
            agent_name="Google Calendar",
            friendly_name="Google Calendar",
            response=f"An error occurred: {error}",
        ).to_dict()


@function_tool(is_enabled=is_google_enabled)
def create_google_calendar_event(wrapper: RunContextWrapper[ChatContext], title: str, timezone: str, start_date: datetime.datetime, end_date: datetime.datetime, location: str | None = None, invitees: list[str] = [], google_meet: bool = False) -> dict:
    """Create Google Calendar event. Only when user explicitly requests.

    Args:
        wrapper: Context with auth
        title: Event name
        timezone: IANA timezone (e.g. "America/New_York")
        start_date: Start datetime (UTC)
        end_date: End datetime (UTC)
        location: Optional physical location
        invitees: Email list for invitations
        google_meet: Add video conference link

    Returns:
        ToolResponse with created event details
    """
    creds = fetch_google_creds(wrapper.context.user_id)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    try:
        service = build("calendar", "v3", credentials=creds)
        event = {
            'summary': title,
            'start': {
                'dateTime': start_date.isoformat(),
                'timeZone': timezone
            },
            'end': {
                'dateTime': end_date.isoformat(),
                'timeZone': timezone
            },
            'location': location,
            'attendees': [{'email': invitee} for invitee in invitees],
            'sendUpdates': 'all',
            'sendNotifications': True,
        }
        if google_meet:
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                }
            }
        print(google_meet)
        event = service.events().insert(calendarId='primary', body=event,
                                        sendUpdates='all', conferenceDataVersion=1).execute()
        return ToolResponse(
            response_type="create_google_calendar_event",
            agent_name="Google Calendar",
            friendly_name="Google Calendar",
            response=event,
        ).to_dict()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return ToolResponse(
            response_type="create_google_calendar_event",
            agent_name="Google Calendar",
            friendly_name="Google Calendar",
            response=f"An error occurred: {error}",
        ).to_dict()


@function_tool(is_enabled=is_google_enabled)
def delete_google_calendar_event(wrapper: RunContextWrapper[ChatContext], event_id: str) -> dict:
    """Delete calendar event permanently. Sends cancellation notices.

    Args:
        wrapper: Context with auth
        event_id: Event ID from get_google_calendar_events

    Returns:
        ToolResponse with success/error message
    """
    creds: Credentials | None = fetch_google_creds(wrapper.context.user_id)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    try:
        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId='primary',
                                eventId=event_id, sendUpdates='all').execute()
        return ToolResponse(
            response_type="delete_google_calendar_event",
            agent_name="Google Calendar",
            friendly_name="Google Calendar",
            response=f"Event {event_id} deleted successfully",
        ).to_dict()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return ToolResponse(
            response_type="delete_google_calendar_event",
            agent_name="Google Calendar",
            friendly_name="Google Calendar",
            response=f"An error occurred: {error}",
        ).to_dict()


GOOGLE_CALENDAR_AGENT = Agent(
    model="gpt-4o",
    name="Google Calendar",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    """Google Calendar assistant. View events, create meetings with attendees/Meet links, delete events. Only create when explicitly requested. Primary calendar only.""",
    handoff_description=RECOMMENDED_PROMPT_PREFIX +
    """Google Calendar: view, create, delete events. Handles attendees, Meet links, timezones.""",
    tools=[get_google_calendar_events,
           create_google_calendar_event, delete_google_calendar_event],
    handoffs=[GOOGLE_DOCS_AGENT]
)

ALL_TOOLS = [get_google_calendar_events,
             create_google_calendar_event, delete_google_calendar_event]
