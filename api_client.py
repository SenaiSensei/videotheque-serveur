"""Seul point d'accès du site à l'API REST."""
import os
import re

import requests
from flask import has_request_context, session

API_URL = os.environ.get("API_URL", "http://api:5000").rstrip("/")
TIMEOUT = 5  # secondes
OBJECT_ID_RE = re.compile(r"^[0-9a-f]{24}$")


class ApiError(Exception):
    """Erreur renvoyée par l'API, ou API injoignable (503 api_unavailable)."""

    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def is_object_id(value):
    return isinstance(value, str) and bool(OBJECT_ID_RE.match(value))


def _check_id(value, code):
    """Refuse un id mal formé avant de l'insérer dans une URL."""
    if not is_object_id(value):
        raise ApiError(404, code, "Ressource introuvable")
    return value


def _request(method, path, json=None, params=None, auth=True):
    headers = {}
    token = session.get("token") if auth and has_request_context() else None
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(method, API_URL + path, json=json, params=params,
                                    headers=headers, timeout=TIMEOUT)
    except requests.RequestException:
        raise ApiError(503, "api_unavailable", "Le service est momentanément indisponible")

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.status_code >= 400:
        raise ApiError(response.status_code,
                       data.get("code", "internal_error"),
                       data.get("message", "Erreur du service"))
    return data


# Films

def get_films(filters=None):
    return _request("GET", "/films", params=filters or {})["films"]


def create_film(film):
    return _request("POST", "/films", json=film)


def get_film(film_id):
    return _request("GET", f"/films/{_check_id(film_id, 'film_not_found')}")


def update_film(film_id, film):
    return _request("PUT", f"/films/{_check_id(film_id, 'film_not_found')}", json=film)


def delete_film(film_id):
    return _request("DELETE", f"/films/{_check_id(film_id, 'film_not_found')}")


# Comptes

def login(email, password):
    """Renvoie {"token": ..., "user": ...}."""
    return _request("POST", "/login", json={"email": email, "password": password}, auth=False)


def create_user(email, username, password):
    """Renvoie {"token": ..., "user": ...}."""
    return _request("POST", "/users", json={"email": email, "username": username, "password": password},
                    auth=False)


def get_users():
    return _request("GET", "/users")["users"]


def get_user(user_id):
    return _request("GET", f"/users/{_check_id(user_id, 'user_not_found')}")


def update_user(user_id, data):
    return _request("PUT", f"/users/{_check_id(user_id, 'user_not_found')}", json=data)


def delete_user(user_id):
    return _request("DELETE", f"/users/{_check_id(user_id, 'user_not_found')}")


def update_roles(user_id, roles):
    return _request("PUT", f"/users/{_check_id(user_id, 'user_not_found')}/roles", json={"roles": roles})


# Favoris

def get_favorites(user_id):
    return _request("GET", f"/users/{_check_id(user_id, 'user_not_found')}/favorites")["films"]


def add_favorite(user_id, film_id):
    return _request("POST", f"/users/{_check_id(user_id, 'user_not_found')}/favorites",
                    json={"film_id": film_id})["favorites"]


def remove_favorite(user_id, film_id):
    return _request("DELETE", f"/users/{_check_id(user_id, 'user_not_found')}/favorites/"
                              f"{_check_id(film_id, 'film_not_found')}")["favorites"]
