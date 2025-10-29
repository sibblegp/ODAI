import json

class ToolResponse:

    def __init__(self, response_type: str, agent_name: str, friendly_name: str, response: dict | str | list, display_response: bool = True):
        self.response_type = response_type
        self.agent_name = agent_name
        self.friendly_name = friendly_name
        self.response = response
        self.display_response = display_response

    def to_dict(self) -> dict:
        return {
            "response_type": self.response_type,
            "agent_name": self.agent_name,
            "friendly_name": self.friendly_name,
            "response": self.response,
            "display_response": self.display_response
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
class OpenWindowResponse(ToolResponse):
    def __init__(self, agent_name: str, url: str):
        self.response_type = 'open_window'
        self.agent_name = agent_name
        self.friendly_name = 'Open Window'
        self.response = {'url': url}
        self.display_response = True
        
class OpenTabResponse(ToolResponse):
    def __init__(self, agent_name: str, url: str):
        self.response_type = 'open_tab'
        self.agent_name = agent_name
        self.friendly_name = 'Open Tab'
        self.response = {'url': url}
        self.display_response = True
        
class AccountNeededResponse(ToolResponse):
    def __init__(self, agent_name: str, account_type: str):
        self.response_type = 'account_needed'
        self.agent_name = agent_name
        self.friendly_name = 'Account Needed'
        self.response = {'account_type': account_type}
        self.display_response = True
        
class GoogleAccountNeededResponse(ToolResponse):
    def __init__(self, agent_name: str):
        self.response_type = 'google_account_needed'
        self.agent_name = agent_name
        self.friendly_name = 'Google Account Needed'
        self.response = {'account_type_needed': 'google'}
        self.display_response = True
        
class ConnectGoogleAccountResponse(ToolResponse):
    def __init__(self, agent_name: str):
        self.response_type = 'connect_google_account'
        self.agent_name = agent_name
        self.friendly_name = 'Connect Google Account'
        self.response = "Please press the button above to connect your Google account"
        self.display_response = True
        
class RequestGoogleAccessResponse(ToolResponse):
    def __init__(self, agent_name: str):
        self.response_type = 'request_google_access'
        self.agent_name = agent_name
        self.friendly_name = 'Request Google Access'
        self.response = "Please press the button above to request access to your Google account"
        self.display_response = True

class ConnectPlaidAccountResponse(ToolResponse):
    def __init__(self, agent_name: str):
        self.response_type = 'connect_plaid_account'
        self.agent_name = agent_name
        self.friendly_name = 'Connect Plaid Account'
        self.response = "Please press the button above to connect your bank or credit card account"
        self.display_response = True
    