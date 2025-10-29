"""Waitlist model for managing email signups."""

import datetime

from ..base import FireStoreObject


class Waitlist(FireStoreObject):
    """Waitlist model for managing email signups."""

    @classmethod
    def add_email(cls, email: str):
        if email is None:
            raise AttributeError("Email is required")
        cls.waitlist.document().set(
            {'email': email, 'created_at': datetime.datetime.now()})

class FakeToken:
    """Fake token class for testing purposes."""
    ciphertext = '1234'
