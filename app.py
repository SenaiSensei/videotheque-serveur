#!/usr/bin/python3
import os
from datetime import timedelta

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)

import api_client as api
import forms
from auth import admin_required, anonymous_required, is_admin, login_required

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),  # même durée que le jeton
)


@app.context_processor
def inject_globals():
    """Variables disponibles dans tous les templates."""
    user = g.get("user")
    return {
        "current_user": user,
        "is_admin": is_admin(user),
        "logged_in": bool(session.get("user_id")),
        "support_types": forms.SUPPORT_TYPES,
    }


def error_page(status, message):
    return render_template("error.html", status=status, message=message), status


# Erreurs

@app.errorhandler(api.ApiError)
def handle_api_error(err):
    if err.status == 401:
        session.clear()
        flash("Votre session a expiré, veuillez vous reconnecter.", "error")
        return redirect(url_for("login"))
    if err.status == 403:
        return error_page(403, "Vous n'avez pas les droits nécessaires.")
    if err.status == 404:
        return error_page(404, err.message)
    if err.status in (400, 409):
        return error_page(400, err.message)
    return error_page(503, "Le service est momentanément indisponible. Réessayez plus tard.")


@app.errorhandler(403)
def forbidden(_):
    return error_page(403, "Vous n'avez pas les droits nécessaires.")


@app.errorhandler(404)
def not_found(_):
    return error_page(404, "Page introuvable.")


@app.errorhandler(405)
def method_not_allowed(_):
    return error_page(405, "Méthode non autorisée.")


# Comptes

@app.route("/")
def index():
    return redirect(url_for("catalog"))


@app.route("/login", methods=["GET", "POST"])
@anonymous_required
def login():
    next_url = forms.safe_next(request.values.get("next"), url_for("catalog"))
    if request.method == "GET":
        return render_template("login.html", form={}, errors=[], next=next_url)

    data, errors = forms.validate_login(request.form)
    if not errors:
        try:
            result = api.login(data["email"], data["password"])
        except api.ApiError as err:
            if err.status not in (400, 401):
                raise
            errors.append("Identifiants incorrects." if err.status == 401 else err.message)
    if errors:
        return render_template("login.html", form={"email": data["email"]}, errors=errors, next=next_url), 400

    _open_session(result)
    flash(f"Bienvenue {result['user']['username']} !", "success")
    return redirect(next_url)


@app.route("/register", methods=["GET", "POST"])
@anonymous_required
def register():
    if request.method == "GET":
        return render_template("register.html", form={}, errors=[])

    data, errors = forms.validate_register(request.form)
    if not errors:
        try:
            result = api.create_user(data["email"], data["username"], data["password"])
        except api.ApiError as err:
            if err.status not in (400, 409):
                raise
            errors.append(err.message)
    if errors:
        form = {"email": data["email"], "username": data["username"]}
        return render_template("register.html", form=form, errors=errors), 400

    _open_session(result)
    flash("Votre compte a été créé.", "success")
    return redirect(url_for("catalog"))


def _open_session(result):
    session.clear()
    session.permanent = True
    session["user_id"] = result["user"]["_id"]
    session["token"] = result["token"]


@app.post("/logout")
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "success")
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "GET":
        return render_template("profile.html", user=g.user, form={"username": g.user["username"]}, errors=[])

    data, errors = forms.validate_profile(request.form)
    if not errors:
        try:
            g.user = api.update_user(g.user["_id"], data)
        except api.ApiError as err:
            if err.status not in (400, 409) and err.code != "invalid_password":
                raise
            errors.append(err.message)
    if errors:
        return render_template("profile.html", user=g.user, form={"username": data["username"]},
                               errors=errors), 400

    flash("Profil mis à jour.", "success")
    return redirect(url_for("profile"))


@app.post("/profile/delete")
@login_required
def delete_account():
    if not request.form.get("confirm"):
        flash("Cochez la case de confirmation pour supprimer votre compte.", "error")
        return redirect(url_for("profile"))
    try:
        api.delete_user(g.user["_id"])
    except api.ApiError as err:
        if err.code != "last_admin":
            raise
        flash(err.message, "error")
        return redirect(url_for("profile"))

    session.clear()
    flash("Votre compte a été supprimé.", "success")
    return redirect(url_for("login"))


# Catalogue

@app.route("/catalog")
@login_required
def catalog():
    filters, errors = forms.search_filters(request.args)
    films = []
    if not errors:
        try:
            films = api.get_films(filters)
        except api.ApiError as err:
            if err.status != 400:
                raise
            errors.append(err.message)
    # Genres proposés dans la liste déroulante : ceux de tout le catalogue,
    # sans doublon ni différence de casse (« Drame » et « drame » ne comptent qu'une fois)
    all_films = films if not filters and not errors else api.get_films()
    genres = {}
    for film in all_films:
        for genre in film["genres"]:
            genres.setdefault(genre.casefold(), genre)
    genres = sorted(genres.values(), key=str.casefold)

    return render_template("catalog.html", films=films, filters=filters, errors=errors,
                           genres=genres, favorites=set(g.user["favorites"]))


@app.route("/films/<film_id>")
@login_required
def film(film_id):
    film = api.get_film(film_id)
    return render_template("film.html", film=film, is_favorite=film["_id"] in g.user["favorites"])


# Favoris

@app.route("/favorites")
@login_required
def favorites():
    return render_template("favorites.html", films=api.get_favorites(g.user["_id"]))


def wants_json():
    """Requête envoyée par favorites.js (fetch), qui attend du JSON plutôt qu'une redirection."""
    return request.headers.get("X-Requested-With") == "fetch"


def favorite_response(is_favorite, message, category="success", status=200):
    """Réponse JSON pour favorites.js, ou message flash et redirection sinon."""
    if wants_json():
        return jsonify({"favorite": is_favorite, "message": message, "category": category}), status
    flash(message, category)
    return redirect(forms.safe_next(request.form.get("next"), url_for("favorites")))


@app.post("/favorites/<film_id>/add")
@login_required
def add_favorite(film_id):
    try:
        api.add_favorite(g.user["_id"], film_id)
    except api.ApiError as err:
        if err.status not in (400, 404):
            raise
        return favorite_response(False, "Ce film n'existe plus.", "error", 404)
    return favorite_response(True, "Film ajouté à vos favoris.")


@app.post("/favorites/<film_id>/remove")
@login_required
def remove_favorite(film_id):
    try:
        api.remove_favorite(g.user["_id"], film_id)
    except api.ApiError as err:
        if err.status != 404:
            raise
        return favorite_response(False, "Film introuvable.", "error", 404)
    return favorite_response(False, "Film retiré de vos favoris.")


# Administration des films

@app.route("/admin/films/new", methods=["GET", "POST"])
@admin_required
def new_film():
    if request.method == "GET":
        return render_template("film_form.html", form=forms.film_to_form({}), errors=[], film_id=None)
    return _save_film(None)


@app.route("/admin/films/<film_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_film(film_id):
    if request.method == "GET":
        film = api.get_film(film_id)
        return render_template("film_form.html", form=forms.film_to_form(film), errors=[], film_id=film_id)
    return _save_film(film_id)


def _save_film(film_id):
    film, errors = forms.film_from_form(request.form)
    if not errors:
        try:
            saved = api.update_film(film_id, film) if film_id else api.create_film(film)
        except api.ApiError as err:
            if err.status != 400:
                raise
            errors.append(err.message)
    if errors:
        return render_template("film_form.html", form=forms.film_form_from_request(request.form),
                               errors=errors, film_id=film_id), 400

    flash("Film enregistré.", "success")
    return redirect(url_for("film", film_id=saved["_id"]))


@app.post("/admin/films/<film_id>/delete")
@admin_required
def delete_film(film_id):
    next_url = forms.safe_next(request.form.get("next"), url_for("catalog"))
    try:
        api.delete_film(film_id)
        flash("Film supprimé.", "success")
    except api.ApiError as err:
        if err.status != 404:
            raise
        flash("Ce film n'existe plus.", "error")
    return redirect(next_url)


# Tableau de bord administrateur

@app.route("/admin")
@admin_required
def dashboard():
    films = api.get_films()
    users = api.get_users()
    stats = {
        "films": len(films),
        "users": len(users),
        "admins": sum("admin" in u["roles"] for u in users),
        "favorites": sum(len(u["favorites"]) for u in users),
        "supports": {kind: sum(any(s["type"] == kind for s in f["supports"]) for f in films)
                     for kind in forms.SUPPORT_TYPES},
        "without_support": sum(not f["supports"] for f in films),
    }
    return render_template("dashboard.html", films=films, users=users, stats=stats)


# Administration des comptes


@app.post("/admin/users/<user_id>/delete")
@admin_required
def admin_delete_user(user_id):
    try:
        api.delete_user(user_id)
    except api.ApiError as err:
        if err.status not in (404, 409):
            raise
        flash(err.message, "error")
        return redirect(url_for("dashboard", _anchor="comptes"))

    if user_id == g.user["_id"]:
        session.clear()
        flash("Votre compte a été supprimé.", "success")
        return redirect(url_for("login"))
    flash("Compte supprimé.", "success")
    return redirect(url_for("dashboard", _anchor="comptes"))


@app.post("/admin/users/<user_id>/roles")
@admin_required
def admin_update_roles(user_id):
    roles = ["user", "admin"] if request.form.get("admin") else ["user"]
    try:
        api.update_roles(user_id, roles)
    except api.ApiError as err:
        if err.status not in (400, 404, 409):
            raise
        flash(err.message, "error")
        return redirect(url_for("dashboard", _anchor="comptes"))

    flash("Rôles mis à jour.", "success")
    if user_id == g.user["_id"] and "admin" not in roles:
        return redirect(url_for("catalog"))  # l'administrateur vient de retirer ses propres droits
    return redirect(url_for("dashboard", _anchor="comptes"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)