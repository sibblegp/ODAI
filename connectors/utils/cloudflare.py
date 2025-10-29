import requests
try:
    from config import Settings
except ImportError:
    from ...config import Settings

SETTINGS = Settings()


class Cloudflare:
    def __init__(self) -> None:
        self.api_key = SETTINGS.cloudflare_api_key
        self.account_id = SETTINGS.cloudflare_account_id
        self.api_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}"

    def render_site_to_markdown(self, url: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body = {
            'url': url
        }
        response = requests.post(f"{self.api_url}/browser-rendering/markdown", headers=headers, json=body)
        data = response.json()
        if data['success']:
            return data['result']
        else:
            raise Exception(data['errors'])