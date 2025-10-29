from fastapi import APIRouter, Form, Response
from typing import Annotated
from agents import Runner
from twilio.twiml.messaging_response import MessagingResponse

try:
    from connectors.utils.context import ChatContext
except ImportError:
    from ..connectors.utils.context import ChatContext

try:
    from config import Settings
except ImportError:
    from ..config import Settings

try:
    from firebase import User, Chat
except ImportError:
    from ..firebase import User, Chat

try:
    from connectors.orchestrator import ORCHESTRATOR_AGENT
except ImportError:
    from ..connectors.orchestrator import ORCHESTRATOR_AGENT

from openai import OpenAI


SETTINGS = Settings()

SMS_ROUTER = APIRouter(prefix='/twilio/sms')

OPENAI_CLIENT = OpenAI(api_key=SETTINGS.openai_api_key)


@SMS_ROUTER.post('/incoming')
async def incoming_sms(
    From: Annotated[str, Form()],
    Body: Annotated[str, Form()],
    FromZip: Annotated[str, Form()]
):
    if SETTINGS.production:
        user = User.get_user_by_id('bBqawe5AuEty3EH2hcw4')
    else:
        user = User.get_user_by_id('lvX2TjNNcYYSroYeJ3LpRuUwwWs1')


    chat = Chat.get_or_create_chat_from_sms(user, From, FromZip)
    context = ChatContext(
        user_id=user.reference_id,
        user=user,
        chat_id=chat.reference_id,
        prompt=Body,
        production=SETTINGS.production,
        project_id=SETTINGS.project_id,
        logged_in=False,
        settings=SETTINGS,
        openai_client=OPENAI_CLIENT,
        is_google_enabled=False,
        is_plaid_enabled=False
    )
    
    last_message_id = getattr(chat, 'last_message_id', None)

    runner = Runner()
    result = await runner.run(ORCHESTRATOR_AGENT, chat.messages + [{"content": Body, "role": "user"}], context=context)
        
    response_body = result.final_output
    
    response = MessagingResponse()
    response.message(response_body, to=From)

    result_input_list = result.to_input_list()
    last_message_id = result.last_response_id
    await chat.update_messages(result_input_list, last_message_id)

    return Response(content=str(response), media_type="text/xml")
