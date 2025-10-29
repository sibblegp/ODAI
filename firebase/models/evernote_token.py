"""EvernoteToken model for managing Evernote OAuth tokens."""

import datetime
from google.cloud.firestore_v1.base_query import FieldFilter

from ..base import FireStoreObject

try:
    from firebase.models.user import User
except ImportError:
    from ..models.user import User

class EvernoteToken(FireStoreObject):
    """EvernoteToken model for managing Evernote OAuth tokens."""

    user_id: str
    oauth_token: str
    oauth_token_secret: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    access_token: str | None

    def __init__(self, media_object) -> None:
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])

    @classmethod
    def start_evernote_token_request(cls, user: 'User', oauth_token: str, oauth_token_secret: str):
        cls.evernote_tokens.document(user.reference_id).set({
            'oauth_token': oauth_token,
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now(),
            'user_id': user.reference_id,
            'oauth_token_secret': oauth_token_secret
        })

    @classmethod
    def retrieve_evernote_token_by_oauth_token(cls, oauth_token: str) -> 'EvernoteToken | None':
        tokens = cls.evernote_tokens.where(
            filter=FieldFilter('oauth_token', '==', oauth_token)).get()
        print(tokens)
        if len(tokens) > 0:
            existing_tokens = cls(tokens[0])
            return existing_tokens
        else:
            return None

    @classmethod
    def get_evernote_token_by_user_id(cls, user_id: str) -> 'EvernoteToken | None':
        token = cls.evernote_tokens.document(user_id).get()
        if token.exists:
            return cls(token)
        else:
            return None

    @classmethod
    def save_evernote_token(cls, user_id: str, access_token: str):
        existing_token = cls.get_evernote_token_by_user_id(user_id)
        if existing_token is None:
            return None
        cls.evernote_tokens.document(user_id).set({
            'user_id': user_id,
            'created_at': existing_token.created_at,
            'access_token': access_token,
            'updated_at': datetime.datetime.now()
        })
