"""User model for managing user accounts and integrations."""

import datetime
import uuid

from ..base import FireStoreObject, SETTINGS, track_google_connected, track_plaid_connected, track_evernote_connected, keys


class User(FireStoreObject):
    """User model for managing user accounts and integrations."""

    name: str
    email: str
    integrations: dict | None
    creationRecorded: bool
    signupRecorded: bool
    key_id: str
    is_registered: bool
    metrics: dict | None
    ready_for_google: str | None

    def __init__(self, media_object) -> None:
        """Initialize a User instance from a Firestore document.
        
        Args:
            media_object: Firestore document reference containing user data
        """
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])

        self.check_has_key_and_generate_if_not()

    @classmethod
    def get_user_by_id(cls, user_id: str) -> 'User | None':
        """Retrieve a user by their ID.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            User object if found, None otherwise
        """
        user = cls.users.document(user_id).get()
        if user.exists:
            return cls(user)
        else:
            return None

    def check_has_key_and_generate_if_not(self):
        """Check if user has an encryption key and generate one if not.
        
        For registered users in non-local environments, ensures they have
        a unique HSM-backed encryption key for sensitive data.
        """
        if SETTINGS.local:
            return

        if hasattr(self, 'is_registered') and self.is_registered == True:
            if not hasattr(self, 'key_id') or self.key_id is None:
                key_id = str(uuid.uuid4())
                key = keys.create_key_hsm(
                    SETTINGS.project_id, 'global', SETTINGS.key_ring_id, key_id)
                self.users.document(self.reference_id).update(
                    {'key_id': key_id})
                self.key_id = key_id

    def record_creation(self):
        """Record that the user account has been created.
        
        Updates the user document to mark creation as recorded.
        
        Returns:
            Self for method chaining
        """
        self.users.document(self.reference_id).update(
            {'creationRecorded': True,
             'signupRecorded': False})
        self.creationRecorded = True
        self.signupRecorded = False
        return self

    def record_signup(self):
        """Record that the user has completed signup.
        
        Updates the user document to mark signup as recorded.
        
        Returns:
            Self for method chaining
        """
        self.users.document(self.reference_id).update(
            {'signupRecorded': True})
        self.signupRecorded = True
        return self

    def set_connected_to_google(self):
        """Mark user as connected to Google services.
        
        Updates the user's integrations to enable Google services
        and tracks the connection event.
        
        Returns:
            Self for method chaining
        """
        if hasattr(self, 'integrations') and self.integrations is not None:
            self.integrations['google'] = True
        else:
            self.integrations = {
                'google': True
            }
        self.users.document(self.reference_id).update(
            {'integrations': self.integrations})
        track_google_connected(self)
        return self

    def check_has_google_account(self):
        """Check if user has connected their Google account.
        
        Returns:
            bool: True if Google is connected, False otherwise
        """
        if hasattr(self, 'integrations') and self.integrations is not None and 'google' in self.integrations and self.integrations['google'] == True:
            return True
        else:
            return False

    @property
    def connected_to_google(self):
        """Check if user has connected their Google account.
        
        Returns:
            bool: True if Google is connected, False otherwise
        """
        return self.check_has_google_account()
        
    def disconnect_from_google(self):
        """Disconnect user from Google services.
        
        Updates the user's integrations to disable Google services.
        
        Returns:
            Self for method chaining
        """
        if hasattr(self, 'integrations') and self.integrations is not None and 'google' in self.integrations and self.integrations['google'] == True:
            self.integrations['google'] = False
            self.users.document(self.reference_id).update(
                {'integrations': self.integrations})
        if hasattr(self, 'ready_for_google') and self.ready_for_google is not None:
            self.ready_for_google = None
            self.users.document(self.reference_id).update(
                {'ready_for_google': self.ready_for_google})
        
        return self

    def set_connected_to_plaid(self):
        """Mark user as connected to Plaid financial services.
        
        Updates the user's integrations to enable Plaid services
        and tracks the connection event.
        
        Returns:
            Self for method chaining
        """
        if hasattr(self, 'integrations') and self.integrations is not None:
            self.integrations['plaid'] = True
        else:
            self.integrations = {
                'plaid': True
            }
        self.users.document(self.reference_id).update(
            {'integrations': self.integrations})
        track_plaid_connected(self)
        return self

    def check_has_plaid_account(self):
        """Check if user has connected their Plaid account.
        
        Returns:
            bool: True if Plaid is connected, False otherwise
        """
        if hasattr(self, 'integrations') and self.integrations is not None and 'plaid' in self.integrations and self.integrations['plaid'] == True:
            return True
        else:
            return False

    @property
    def connected_to_plaid(self):
        """Check if user has connected their Plaid account.
        
        Returns:
            bool: True if Plaid is connected, False otherwise
        """
        return self.check_has_plaid_account()


    def disconnect_from_plaid(self):
        """Disconnect user from Plaid services.
        
        Updates the user's integrations to disable Plaid services.
        
        Returns:
            Self for method chaining
        """
        if hasattr(self, 'integrations') and self.integrations is not None and 'plaid' in self.integrations and self.integrations['plaid'] == True:
            self.integrations['plaid'] = False
            self.users.document(self.reference_id).update(
                {'integrations': self.integrations})
        
        return self

    def set_connected_to_evernote(self):
        """Mark user as connected to Evernote services.
        
        Updates the user's integrations to enable Evernote services
        and tracks the connection event.
        
        Returns:
            Self for method chaining
        """
        if hasattr(self, 'integrations') and self.integrations is not None:
            self.integrations['evernote'] = True
        else:
            self.integrations = {
                'evernote': True
            }
        self.users.document(self.reference_id).update(
            {'integrations': self.integrations})
        track_evernote_connected(self)
        return self

    def check_has_evernote_account(self):
        """Check if user has connected their Evernote account.
        
        Returns:
            bool: True if Evernote is connected, False otherwise
        """
        if hasattr(self, 'integrations') and self.integrations is not None and 'evernote' in self.integrations and self.integrations['evernote'] == True:
            return True
        else:
            return False

    def check_terms_of_service_accepted(self):
        """Check if user has accepted the terms of service.
        
        Returns:
            bool: True if terms are accepted, False otherwise
        """
        if hasattr(self, 'termsAccepted') and self.termsAccepted == True:
            return True
        else:
            return False
        
    def add_prompt_to_metrics(self, prompt: str):
        """Add a user prompt to metrics tracking.
        
        Records the prompt text and timestamp for analytics.
        
        Args:
            prompt: The user's prompt text
            
        Returns:
            Self for method chaining
        """
        if hasattr(self, 'metrics') and self.metrics is not None:
            self.metrics['prompts'] = self.metrics.get('prompts', [])
            self.metrics['prompts'].append({'prompt': prompt, 'timestamp': datetime.datetime.now().isoformat()})
            self.metrics['prompt_count'] = self.metrics.get('prompt_count', 0) + 1
        else:
            self.metrics = {'prompts': [{'prompt': prompt, 'timestamp': datetime.datetime.now().isoformat()}], 'prompt_count': 1}
        self.users.document(self.reference_id).update(
            {'metrics': self.metrics})
        return self
    
    def add_tool_call_to_metrics(self, tool_call: str):
        """Add a tool call to metrics tracking.
        
        Increments the count for the specific tool being called.
        
        Args:
            tool_call: Name of the tool being called
            
        Returns:
            Self for method chaining
        """
        print(f"Adding tool call to metrics: {tool_call}")
        if hasattr(self, 'metrics') and self.metrics is not None:
            self.metrics['tool_calls'] = self.metrics.get('tool_calls', {})
            self.metrics['tool_calls'][tool_call] = self.metrics['tool_calls'].get(tool_call, 0) + 1
            self.metrics['tool_call_count'] = self.metrics.get('tool_call_count', 0) + 1
        else:
            self.metrics = {'tool_calls': {tool_call: 1}, 'tool_call_count': 1}
        self.users.document(self.reference_id).update(
            {'metrics': self.metrics})
        return self
    
    def add_agent_call_to_metrics(self, agent_name: str):
        """Add an agent call to metrics tracking.
        
        Increments the count for the specific agent being called.
        
        Args:
            agent_name: Name of the agent being called
            
        Returns:
            Self for method chaining
        """
        if hasattr(self, 'metrics') and self.metrics is not None:
            self.metrics['agent_calls'] = self.metrics.get('agent_calls', {})
            self.metrics['agent_calls'][agent_name] = self.metrics['agent_calls'].get(agent_name, 0) + 1
            self.metrics['agent_call_count'] = self.metrics.get('agent_call_count', 0) + 1
        else:
            self.metrics = {'agent_calls': {agent_name: 1}, 'agent_call_count': 1}
        self.users.document(self.reference_id).update(
            {'metrics': self.metrics})
        return self