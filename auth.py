"""Contrôles d'accès du site : session, utilisateur connecté, administrateur."""
from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for

import api_client as api


def is_admin(user):
    return bool(user) and "admin" in user.get("roles", [])


def current_path():
    """Page demandée, pour y revenir après la connexion (GET uniquement)."""
    return request.full_path.rstrip("?") if request.method == "GET" else None


def end_session(message="Votre session a expiré, veuillez vous reconnecter."):
    session.clear()
    flash(message, "error")
    return redirect(url_for("login", next=current_path()))


def login_required(view):
    """Contrôle utilisateur : session présente, puis compte rechargé depuis l'API."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id") or not session.get("token"):
            return redirect(url_for("login", next=current_path()))
        try:
            g.user = api.get_user(session["user_id"])
        except api.ApiError as err:
            if err.status in (401, 403, 404):
                return end_session()
            raise
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    """Contrôle administrateur : contrôle utilisateur, puis rôle admin."""
    @login_required
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_admin(g.user):
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def anonymous_required(view):
    """Pages réservées aux visiteurs non connectés (connexion, inscription)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("user_id"):
            return redirect(url_for("catalog"))
        return view(*args, **kwargs)
    return wrapper
