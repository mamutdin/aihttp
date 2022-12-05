import requests
import json
from typing import Literal
from tests.config import API_URL

session = requests.Session()


def get_item(url, d: dict, key1, key2):
    response = requests.get(url)
    json_data = response.json()
    name = json_data[key1]
    d[key2] = name


def get_items(urls: list, d: dict, key1, key2):
    l = []
    for url in urls:
        response = requests.get(url)
        json_data = response.json()
        l.append(json_data[key1])
    l = ', '.join(l)
    d[key2] = l


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


def create_user(person_id: int) -> dict:
    response = requests.get(f'https://swapi.dev/api/people/{person_id}')
    json_data = response.json()
    json_data['ID'] = person_id

    if 'detail' not in json_data:
        result2 = {key: val for key, val in json_data.items() if
                   key != 'created' and key != 'edited' and key != 'url'}
        get_item(json_data['homeworld'], result2, 'name', 'homeworld')
        get_items(json_data['films'], result2, 'title', 'films')
        get_items(json_data['species'], result2, 'name', 'species')
        get_items(json_data['starships'], result2, 'name', 'starships')
        get_items(json_data['vehicles'], result2, 'name', 'vehicles')
        return base_request("post", "people/", json={"json": result2})


def get_user(person_id: int) -> dict:
    return base_request("get", f"people/{person_id}")


def patch_user(person_id: int, patch: dict) -> dict:
    return base_request("patch", f"people/{person_id}", json=patch)


def delete_user(person_id: int) -> dict:
    return base_request("delete", f"people/{person_id}")
