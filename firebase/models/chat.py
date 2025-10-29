"""Chat model for managing chat conversations."""

import datetime
import json
import uuid
from google.cloud.firestore_v1.base_query import FieldFilter
try:
    from base import FireStoreObject, client
except ImportError:
    from ..base import FireStoreObject, client

try:
    from firebase.models.user import User
    from firebase.models.google_token import GoogleToken
    from firebase.models.plaid_token import PlaidToken
except ImportError:
    from ..models.user import User
    from ..models.google_token import GoogleToken
    from ..models.plaid_token import PlaidToken

try:
    from config import Settings
except ImportError:
    from ...config import Settings
from openai import OpenAI
from fastapi import HTTPException

SETTINGS = Settings()

OPENAI_CLIENT = OpenAI(api_key=SETTINGS.openai_api_key)


class Chat(FireStoreObject):
    """
    Represents a chat object.

    Attributes:
        __media_object: The underlying media object.
        reference_id: The reference ID of the media object.
    """

    __media_object = None
    last_message_id: str | None
    title: str | None
    messages: list[dict]
    responses: list[dict]
    from_number: str | None
    zip_code: str | None
    original_ip: str | None
    expires_at: datetime.datetime | None
    user_id: str | None
    deleted: bool
    created_at: datetime.datetime
    token_usage: dict

    def __init__(self, media_object) -> None:
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])

    @classmethod
    def get_chat_by_id(cls, chat_id: str, user_id: str) -> 'Chat | None':
        chat = cls.chats.document(chat_id).get()
        if chat.exists:
            chat_object = cls(chat)
            if chat_object.user_id != user_id:
                raise HTTPException(status_code=403, detail="You are not authorized to access this chat.")
            return chat_object
        else:
            return None
        
        

    @classmethod
    def create_chat(cls, chat_id: str, user: 'User', latitude_longitude: str, city_state_country: str, timezone: str, ip: str) -> 'Chat':
        # Import User here to avoid circular imports

        if hasattr(user, 'name') and user.name is not None:
            name = user.name
        else:
            name = None

        if hasattr(user, 'email') and user.email is not None:
            email = user.email
        else:
            email = None

        # Get Google accounts
        google_accounts = []
        if user.connected_to_google == True:
            google_token = GoogleToken.get_tokens_by_user_id(user.reference_id)
            if google_token is not None:
                for account in google_token.accounts:
                    google_accounts.append(
                        google_token.accounts[account]['email'])

        # Get Plaid accounts
        plaid_accounts = []
        if user.connected_to_plaid == True:
            plaid_token = PlaidToken.get_tokens_by_user_id(user.reference_id)
            if plaid_token is not None:
                for token in plaid_token.tokens:
                    plaid_accounts += [account['name']
                                       for account in token['account_names_and_numbers']]

        # Build system message
        message = 'You are ODAI, a personal assistant connected to many difference services. You should answer questions to the best of your ability. Be friendly, conversational, helpful, and courteous.The current datetime is ' + datetime.datetime.now(
            tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + ' UTC. Make sure to take into account daylight savings time. '
        if name:
            message += ' My name is ' + name + '. '
        if email:
            message += ' My email is ' + email + '. '
        message += ' My current timezone is ' + timezone + '. My location is ' + latitude_longitude + ' in ' + city_state_country + \
            '. In responses translate any timezone into the standard US timezones like Eastern, Central, Mountain, Pacific, etc. '

        if len(google_accounts) > 0:
            message += ' I am connected to the following Google accounts: ' + \
                ', '.join(google_accounts) + '. '
        else:
            message += ' I am not connected to any Google accounts. '
            message += ' If I am not connected to a Google account, do not connect me to the GMAIL, Google Calendar, or Google Docs agents except for the Google Connector agent. '

        if len(plaid_accounts) > 0:
            message += ' I am connected to the following Bank, credit card, and investment accounts through Plaid: ' + \
                ', '.join(plaid_accounts) + '. '
        else:
            message += ' I am not connected to any Bank, credit card, or investment accounts through Plaid. '
            message += ' If I am not connected to a Bank, credit card, or investment account through Plaid, do not connect me to the Bank, credit card, or investment account agents except for the Plaid Connector agent.'

        message += ' If showing a URL, make it a clickable link instead of displaying the URL. If you were not able to answer the user\'s question, suggest a follow up question using one of the agents/tools you are connected to to get the information if possible.'

        cls.chats.document(chat_id).set({
            'original_ip': ip,
            'expires_at': datetime.datetime.now() + datetime.timedelta(days=5),
            'user_id': user.reference_id,
            'deleted': False,
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now(),
            'messages': [{'content': message, 'role': 'system'}],
            'display_in_search': False,
            'chat_token_usage': {
                'input_tokens': 0,
                'cached_input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0
            }
        })
        return cls(cls.chats.document(chat_id).get())

    @classmethod
    def get_or_create_chat_from_sms(cls, user: 'User', from_number: str, zip_code: str) -> 'Chat':
        chat = cls.chats.where(filter=FieldFilter('user_id', '==', user.reference_id)).where(
            filter=FieldFilter('from_number', '==', from_number)).get()
        if len(chat) > 0:
            return cls(chat[0])
        timezone = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{'role': 'user', 'content': 'What is the timezone of ' + zip_code +
                       '? Respond with a JSON object with the key "timezone" and the value being the timezone in the format of "America/New_York".'}],
            response_format={'type': 'json_object'}
        )
        timezone = json.loads(timezone.choices[0].message.content)['timezone']

        message = 'The current datetime is ' + datetime.datetime.now(
            tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + ' UTC. Make sure to take into account daylight savings time. '
        message += ' My current timezone is ' + timezone + '. '
        message += ' My location is ' + zip_code + '. '
        message += ' In responses translate any timezone into the standard US timezones like Eastern, Central, Mountain, Pacific, etc. '
        message += 'You are a helpful SMS assistant. Format your messages in a way that is appropriate for an SMS conversation.'

        chat_id = str(uuid.uuid4())
        message += ' If showing a URL, make it a clickable link instead of displaying the URL.'
        cls.chats.document(chat_id).set({
            'user_id': user.reference_id,
            'from_number': from_number,
            'zip_code': zip_code,
            'deleted': False,
            'expires_at': datetime.datetime.now() + datetime.timedelta(days=5),
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now(),
            'messages': [{'content': message, 'role': 'system'}],
            'display_in_search': False,
            'chat_token_usage': {
                'input_tokens': 0,
                'cached_input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0
            }
        })
        return cls(cls.chats.document(chat_id).get())

    def add_message(self, message: str):
        self.messages.append({'content': message, 'role': 'user'})
        self.chats.document(self.reference_id).update(
            {'messages': self.messages})

    async def update_messages(self, messages: list, last_message_id: str | None):
        self.messages = messages
        # NOTE: Exclude the system message from the title generation
        existing_messages = json.dumps(messages[1:])
        chat_title = client.chat.completions.create(
            model="gpt-4o",
            messages=[{'role': 'user', 'content': existing_messages}, {
                "role": "user", "content": "Give back a title for this chat under 30 characters. Don't wrap it in quotes or use any other formatting."}]
        )
        self.title = chat_title.choices[0].message.content
        self.chats.document(self.reference_id).update({
            'messages': self.messages,
            'title': chat_title.choices[0].message.content,
            'expires_at': datetime.datetime.now() + datetime.timedelta(weeks=1000),
            'display_in_search': True,
            'last_message_id': last_message_id
        })
        return self

    async def add_responses(self, responses: list):
        if hasattr(self, 'responses'):
            self.responses.extend(responses)
            self.chats.document(self.reference_id).update(
                {'responses': self.responses})
        else:
            self.responses = responses
            self.chats.document(self.reference_id).update(
                {'responses': self.responses})
        return self

    def update_timestamp(self):
        self.updated_at = datetime.datetime.now()
        self.messages.append({'content': 'The current datetime now is ' + datetime.datetime.now(
            tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + ' UTC.', 'role': 'system'})
        return self

    async def update_token_usage(self, input_tokens: int, cached_input_tokens: int, output_tokens: int):
        if hasattr(self, 'chat_token_usage'):
            self.chat_token_usage['input_tokens'] += input_tokens
            self.chat_token_usage['cached_input_tokens'] += cached_input_tokens
            self.chat_token_usage['output_tokens'] += output_tokens
            self.chat_token_usage['total_tokens'] += input_tokens + \
                cached_input_tokens + output_tokens
            self.chats.document(self.reference_id).update(
                {'chat_token_usage': self.chat_token_usage})
            return self
        else:
            self.chat_token_usage = {
                'input_tokens': input_tokens,
                'cached_input_tokens': cached_input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + cached_input_tokens + output_tokens
            }
            self.chats.document(self.reference_id).update(
                {'chat_token_usage': self.chat_token_usage})
            return self
