"""PlaidToken model for managing Plaid banking tokens."""

import datetime
import json
import base64
import uuid
from google.cloud.firestore_v1.base_query import FieldFilter

from ..base import FireStoreObject, SETTINGS, keys, client

try:
    from firebase.models.user import User
except ImportError:
    from ..models.user import User


class PlaidToken(FireStoreObject):
    """PlaidToken model for managing Plaid banking tokens."""

    tokens: list
    user_id: str
    created_at: datetime.datetime
    redirect_uri: str

    def __init__(self, media_object) -> None:
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])

    @classmethod
    def create_token_request(cls, user: 'User', redirect_uri: str | None) -> 'PlaidToken':
        existing_request = cls.plaid_tokens.document(user.reference_id).get()

        if existing_request.exists:
            return cls(existing_request)
        else:
            token = cls.plaid_tokens.document(user.reference_id).set(
                {'created_at': datetime.datetime.now(), 'user_id': user.reference_id, 'redirect_uri': redirect_uri, 'tokens': []})
            token = cls.plaid_tokens.document(user.reference_id).get()
            return cls(token)

    @classmethod
    def save_or_add_token(cls, account_names_and_numbers: dict, auth_token: str, item_id: str, user: 'User', bank_name: str) -> 'PlaidToken':
        existing_token_request = cls.plaid_tokens.document(
            user.reference_id).get()
        if not existing_token_request.exists:
            raise Exception('Invalid request')

        account_names = ', '.join([account['name']
                                  for account in account_names_and_numbers])

        # response = client.chat.completions.create(
        #     model="gpt-4o",
        #     messages=[{'role': 'user', 'content': 'Give me back the name of the bank, credit card company, or other financial institution for the following accounts: ' + account_names + '. If you don\'t know, come up with a title that can be used to identify the bank or credit card company. Respond in JSON format in the following format: {"financial_institution_name": "name"}'}],
        #     response_format={"type": "json_object"}
        # )
        # bank_name = json.loads(response.choices[0].message.content)['financial_institution_name']
        # if bank_name is None:
        #     bank_name = 'Unknown'

        existing_token = cls(cls.plaid_tokens.document(
            existing_token_request.reference.id).get())
        if not SETTINGS.local:
            encrypted_auth_token_response = keys.encrypt_symmetric(
                SETTINGS.project_id, 'global', SETTINGS.key_ring_id, user.key_id, auth_token)
            encrypted_item_id_response = keys.encrypt_symmetric(
                SETTINGS.project_id, 'global', SETTINGS.key_ring_id, user.key_id, item_id)
            encrypted_auth_token = base64.b64encode(
                encrypted_auth_token_response.ciphertext).decode('utf-8')
            encrypted_item_id = base64.b64encode(
                encrypted_item_id_response.ciphertext).decode('utf-8')
        else:
            encrypted_auth_token = base64.b64encode(
                auth_token.encode('utf-8')).decode('utf-8')
            encrypted_item_id = base64.b64encode(
                item_id.encode('utf-8')).decode('utf-8')

        if hasattr(existing_token, 'tokens'):
            existing_token.tokens.append({
                'valid': True,
                'created_at': datetime.datetime.now(),
                'auth_token': encrypted_auth_token,
                'item_id': encrypted_item_id,
                'account_names_and_numbers': account_names_and_numbers,
                'bank_name': bank_name,
                'id': str(uuid.uuid4())
            })
            cls.plaid_tokens.document(existing_token.reference_id).update({
                'tokens': existing_token.tokens})
        else:
            existing_token.tokens = [{
                'valid': True,
                'created_at': datetime.datetime.now(),
                'auth_token': encrypted_auth_token,
                'item_id': encrypted_item_id,
                'account_names_and_numbers': account_names_and_numbers,
                'bank_name': bank_name,
                'id': str(uuid.uuid4())
            }]
            cls.plaid_tokens.document(existing_token.reference_id).update({
                'tokens': existing_token.tokens})

        user.set_connected_to_plaid()
        return existing_token

    @classmethod
    def get_tokens_by_user_id(cls, user_id: str) -> 'PlaidToken | None':
        tokens = cls.plaid_tokens.document(user_id).get()
        if tokens.exists:
            existing_tokens = cls(tokens)
            return existing_tokens
        else:
            return None

    @classmethod
    def get_accounts_by_user_id(cls, user_id: str) -> list[dict]:
        user_tokens = cls.plaid_tokens.document(user_id).get()
        if not user_tokens.exists:
            return []
        plaid_token = cls(user_tokens)
        available_accounts = []
        for account in plaid_token.tokens:
            if account['valid']:
                available_accounts.append(
                    {'bank_name': account['bank_name'], 'mask': account['account_names_and_numbers'], 'id': account['id']})
        return available_accounts

    @classmethod
    def reset_tokens(cls, user_id: str) -> bool:
        tokens = cls.plaid_tokens.document(user_id).get()
        if tokens.exists:
            tokens.reference.delete()
            return True
        else:
            return False

    def decrypted_tokens(self) -> list[dict]:
        from .user import User

        user = User.get_user_by_id(self.user_id)
        if user is None:
            return []
        decrypted_tokens = []
        for account in self.tokens:
            if account['valid'] == False:
                continue
            if SETTINGS.local:
                decrypted_auth_token = base64.b64decode(
                    account['auth_token']).decode('utf-8')
                decrypted_item_id = base64.b64decode(
                    account['item_id']).decode('utf-8')
                decrypted_tokens.append({
                    'auth_token': decrypted_auth_token,
                    'item_id': decrypted_item_id,
                    'account_names_and_numbers': account['account_names_and_numbers']
                })
            else:
                decrypted_auth_token = keys.decrypt_symmetric(
                    SETTINGS.project_id, 'global', SETTINGS.key_ring_id, user.key_id, base64.b64decode(account['auth_token']))
                decrypted_item_id = keys.decrypt_symmetric(
                    SETTINGS.project_id, 'global', SETTINGS.key_ring_id, user.key_id, base64.b64decode(account['item_id']))
                decrypted_tokens.append({
                    'auth_token': decrypted_auth_token.plaintext.decode('utf-8'),
                    'item_id': decrypted_item_id.plaintext.decode('utf-8'),
                    'account_names_and_numbers': account['account_names_and_numbers']
                })
        return decrypted_tokens

    def delete_account(self, user: User, account_id: str) -> bool:
        for account in self.tokens:
            if account['id'] == account_id:
                account['valid'] = False
                self.tokens.remove(account)
                self.plaid_tokens.document(self.reference_id).update({
                    'tokens': self.tokens})
                if len(self.tokens) == 0:
                    user.disconnect_from_plaid()
                return True
        return False
