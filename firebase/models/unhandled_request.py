"""UnhandledRequest model for tracking requests that couldn't be handled."""

import datetime

from ..base import FireStoreObject

try:
    from firebase.models.user import User
    from firebase.models.chat import Chat
except ImportError:
    from ..models.user import User
    from ..models.chat import Chat

class UnhandledRequest(FireStoreObject):
    """UnhandledRequest model for tracking requests that couldn't be handled."""

    user_id: str
    chat_id: str
    prompt: str
    capability_requested: str
    capability_description: str
    created_at: datetime.datetime

    def __init__(self, media_object) -> None:
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])

    @classmethod
    async def create_unhandled_request(cls, user: 'User', chat: 'Chat', prompt: str, capability_requested: str, capability_description: str):
        cls.unhandled_requests.document().set({
            'user_id': user.reference_id,
            'chat_id': chat.reference_id,
            'prompt': prompt,
            'capability_requested': capability_requested,
            'capability_description': capability_description,
            'created_at': datetime.datetime.now()
        })
        return True
