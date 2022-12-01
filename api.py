import requests
import json
from typing import Literal
from config import API_URL

session = requests.Session()


class HttpError(Exception):
    def __init__(self, status_code: int, message: dict | str):
        self.status_code = status_code
        self.message = message


def base_request(method: Literal["get", "post", "delete", "patch"], path: str, *args, **kwargs) -> dict:
    method = getattr(session, method)
    response = method(f"{API_URL}/{path}", *args, **kwargs)
    if response.status_code >= 400:
        try:
            message = response.json()
        except json.decoder.JSONDecodeError:
            message = response.text

        raise HttpError(response.status_code, message)
    return response.json()


def create_user(person_id: str) -> dict:
    return base_request("post", "users/", json={"ID": person_id})


def get_user(user_id: int) -> dict:
    return base_request("get", f"users/{user_id}")


def patch_user(user_id: int, patch: dict) -> dict:
    return base_request("patch", f"users/{user_id}", json=patch)


def delete_user(user_id: int) -> dict:
    return base_request("delete", f"users/{user_id}")
