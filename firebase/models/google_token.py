"""GoogleToken model for managing Google OAuth tokens."""

import datetime
import json
import base64
from google.cloud.firestore_v1.base_query import FieldFilter

from ..base import FireStoreObject, SETTINGS, keys

try:
    from firebase.models.user import User
except ImportError:
    from ..models.user import User


class GoogleToken(FireStoreObject):
    """GoogleToken model for managing Google OAuth tokens."""

    accounts: dict
    user_id: str
    state: str
    created_at: datetime.datetime
    redirect_uri: str

    def __init__(self, media_object) -> None:
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])

    @classmethod
    def create_token_request(cls, user: 'User', state: str, redirect_uri: str) -> 'GoogleToken':
        existing_request = cls.google_tokens.document(user.reference_id).get()

        if existing_request.exists:
            cls.google_tokens.document(user.reference_id).update({'state': state, 'created_at': datetime.datetime.now(
            ), 'user_id': user.reference_id, 'redirect_uri': redirect_uri})
            return cls(cls.google_tokens.document(user.reference_id).get())
        else:
            cls.google_tokens.document(user.reference_id).set(
                {'state': state, 'created_at': datetime.datetime.now(), 'user_id': user.reference_id, 'redirect_uri': redirect_uri, 'accounts': {}})
            return cls(cls.google_tokens.document(user.reference_id).get())

    @classmethod
    def save_or_add_token(cls, state: str, token: dict, user_info: dict) -> 'GoogleToken':
        from .user import User

        existing_token_request = cls.google_tokens.where(filter=FieldFilter('state', '==', state)).where(
            filter=FieldFilter('created_at', '>', datetime.datetime.now() - datetime.timedelta(minutes=10))).get()
        if len(existing_token_request) == 0:
            raise Exception('Invalid state')
        existing_token = cls(cls.google_tokens.document(
            existing_token_request[0].reference.id).get())
        user = User.get_user_by_id(existing_token.user_id)
        if user is None:
            raise Exception('Invalid user')
        if not SETTINGS.local:
            encrypted_response = keys.encrypt_symmetric(
                SETTINGS.project_id, 'global', SETTINGS.key_ring_id, user.key_id, json.dumps(token))
            encrypted_token = base64.b64encode(
                encrypted_response.ciphertext).decode('utf-8')
        else:
            encrypted_token = base64.b64encode(
                json.dumps(token).encode('utf-8')).decode('utf-8')
        default = None
        new_default = False
        if hasattr(existing_token, 'accounts'):
            for account in existing_token.accounts:
                default = existing_token.accounts[account]['default']
        if default is None:
            new_default = True

        if hasattr(existing_token, 'accounts'):
            if user_info['email'] not in existing_token.accounts:
                existing_token.accounts[user_info['email']] = {
                    'email': user_info['email'],
                    'name': user_info['name'],
                    'picture': user_info['picture'],
                    'created_at': datetime.datetime.now(),
                    'token': encrypted_token,
                    'default': new_default
                }
                cls.google_tokens.document(existing_token.reference_id).update({
                    'accounts': existing_token.accounts})
            else:
                existing_token.accounts[user_info['email']
                                        ]['token'] = encrypted_token
                cls.google_tokens.document(existing_token.reference_id).update({
                    'accounts': existing_token.accounts})
        else:
            existing_token.accounts = {user_info['email']: {
                'email': user_info['email'],
                'name': user_info['name'],
                'picture': user_info['picture'],
                'created_at': datetime.datetime.now(),
                'token': encrypted_token,
                'default': new_default
            }}
            cls.google_tokens.document(existing_token.reference_id).update({
                'accounts': existing_token.accounts})

        user.set_connected_to_google()
        return existing_token

    @classmethod
    def get_tokens_by_user_id(cls, user_id: str) -> 'GoogleToken | None':
        token = cls.google_tokens.document(user_id).get()
        if token.exists:
            return cls(token)
        else:
            return None
        
    @classmethod
    def reset_tokens(cls, user_id: str) -> bool:
        tokens = cls.google_tokens.where(filter=FieldFilter('user_id', '==', user_id)).get()
        if len(tokens) > 0:
            tokens[0].reference.delete()
            return True
        else:
            return False

    def get_default_account_credentials(self) -> dict | None:
        from .user import User

        user = User.get_user_by_id(self.user_id)
        if user is None:
            return None
        if hasattr(self, 'accounts'):
            for account in self.accounts:
                if self.accounts[account]['default'] == True:
                    if SETTINGS.local:
                        decrypted_token = base64.b64decode(
                            self.accounts[account]['token']).decode('utf-8')
                        return json.loads(decrypted_token)
                    else:
                        decrypted_token = keys.decrypt_symmetric(
                            SETTINGS.project_id, 'global', SETTINGS.key_ring_id, user.key_id, base64.b64decode(self.accounts[account]['token']))
                        return json.loads(decrypted_token.plaintext)
        return None
