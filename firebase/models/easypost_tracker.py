"""EasyPostTracker model for managing package tracking."""

import datetime
from google.cloud.firestore_v1.base_query import FieldFilter

from ..base import FireStoreObject

try:
    from firebase.models.user import User
except ImportError:
    from ..models.user import User


class EasyPostTracker(FireStoreObject):
    """EasyPostTracker model for managing package tracking."""

    user_id: str
    tracking_number: str
    carrier: str
    easypost_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    def __init__(self, media_object) -> None:
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])

    @classmethod
    def create_tracker(cls, user: 'User', tracking_number: str, carrier: str, easypost_id: str):
        cls.easypost_trackers.document().set({
            'user_id': user.reference_id,
            'tracking_number': tracking_number,
            'carrier': carrier,
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now(),
            'easypost_id': easypost_id
        })
        return cls.get_tracker_by_tracking_number(tracking_number)

    @classmethod
    def get_trackers_by_user_id(cls, user_id: str) -> list['EasyPostTracker']:
        trackers = cls.easypost_trackers.where(
            filter=FieldFilter('user_id', '==', user_id)).get()
        return [cls(tracker) for tracker in trackers]

    @classmethod
    def get_tracker_by_tracking_number(cls, tracking_number: str) -> 'EasyPostTracker | None':
        tracker = cls.easypost_trackers.where(filter=FieldFilter(
            'tracking_number', '==', tracking_number)).get()
        if len(tracker) > 0:
            return cls(tracker[0])
        else:
            return None
