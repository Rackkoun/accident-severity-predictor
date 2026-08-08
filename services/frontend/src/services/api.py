"""
frontend api service
"""

import requests

from services.frontend.src.config.settings import settings


class APIService:
    def __init__(self) -> None:
        self.base_url = settings.backend_url + settings.api_prefix
        self.session = requests.Session()  # to save api access session

    def get(self, endpoint: str) -> requests.Response:

        return self.session.get(
            self.base_url + endpoint,
            timeout=3,
        )


api_client = APIService()
