"""Requesting access to Google services."""

import datetime
import json
import base64
from google.cloud.firestore_v1.base_query import FieldFilter

from ..base import FireStoreObject, SETTINGS, keys

try:
    from firebase.models.user import User
except ImportError:
    from ..models.user import User


class GoogleAccessRequest(FireStoreObject):
    """Requesting access to Google services."""

    email: str
    created_at: datetime.datetime

    def __init__(self, media_object) -> None:
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])
            
    @classmethod
    def create_request(cls, user, email: str) -> 'GoogleAccessRequest':
        existing_request = cls.google_access_requests.where(filter=FieldFilter('user_id', '==', user.reference_id)).get()
        if len(existing_request) > 0:
            return True
        cls.google_access_requests.document().set({'email': email, 'created_at': datetime.datetime.now(), 'user_id': user.reference_id, 'completed': False, 'user_email': user.email, 'user_name': user.name})
        return True
    
    @classmethod
    def get_request_for_user(cls, user_id: str) -> 'GoogleAccessRequest':
        requests = cls.google_access_requests.where(filter=FieldFilter('user_id', '==', user_id)).get()
        if len(requests) == 0:
            return None
        return requests[0]