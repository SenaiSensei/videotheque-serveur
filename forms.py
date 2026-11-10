"""Validation des formulaires et conversion en JSON pour l'API."""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://[^\s<>\"']+$")
SUPPORT_TYPES = {"dvd": "DVD", "bluray": "Blu-ray", "digital": "Numérique"}
SEARCH_FIELDS = ("title", "director", "actor", "genre", "year", "support")


def _get(form, key):
    return form.get(key, "").strip()


def _check_username(username, errors):
    if not 3 <= len(username) <= 30:
        errors.append("Le nom d'utilisateur doit contenir entre 3 et 30 caractères.")


def _check_password(password, errors, label="Le mot de passe"):
    if not 8 <= len(password) <= 128:
        errors.append(f"{label} doit contenir entre 8 et 128 caractères.")


# Comptes

def validate_login(form):
    data = {"email": _get(form, "email").lower(), "password": form.get("password", "")}
    errors = []
    if not data["email"] or not data["password"]:
        errors.append("L'email et le mot de passe sont obligatoires.")
    elif not EMAIL_RE.match(data["email"]):
        errors.append("Format d'email invalide.")
    return data, errors


def validate_register(form):
    data = {
        "email": _get(form, "email").lower(),
        "username": _get(form, "username"),
        "password": form.get("password", ""),
    }
    errors = []
    if not EMAIL_RE.match(data["email"]):
        errors.append("Format d'email invalide.")
    _check_username(data["username"], errors)
    _check_password(data["password"], errors)
    if data["password"] != form.get("password_confirm", data["password"]):
        errors.append("Les deux mots de passe ne correspondent pas.")
    return data, errors


def validate_profile(form):
    """Renvoie le JSON pour PUT /users/{id}, sans mot de passe s'il n'est pas changé."""
    data = {"username": _get(form, "username")}
    errors = []
    _check_username(data["username"], errors)

    current = form.get("current_password", "")
    new = form.get("new_password", "")
    if current or new:
        if not current:
            errors.append("Le mot de passe actuel est obligatoire pour en choisir un nouveau.")
        _check_password(new, errors, "Le nouveau mot de passe")
        if new != form.get("new_password_confirm", new):
            errors.append("Les deux nouveaux mots de passe ne correspondent pas.")
        data["current_password"] = current
        data["new_password"] = new
    return data, errors


# Recherche

def search_filters(args):
    """Garde les filtres renseignés de l'URL et les vérifie."""
    filters = {key: args.get(key, "").strip() for key in SEARCH_FIELDS}
    filters = {key: value for key, value in filters.items() if value}
    errors = []
    if "year" in filters and not filters["year"].isdigit():
        errors.append("L'année doit être un nombre entier.")
    if "support" in filters and filters["support"] not in SUPPORT_TYPES:
        errors.append("Support inconnu.")
    return filters, errors


# Films

def film_from_form(form):
    """Construit le Film JSON à partir du formulaire.

    Champs attendus : title, description, year, director_last_name, director_first_name,
    genres (séparés par des virgules), actor_last_name[] et actor_first_name[],
    support_type[] et support_location[], poster_url (facultatif). Les lignes vides sont ignorées.
    """
    errors = []

    year_text = _get(form, "year")
    year = int(year_text) if year_text.isdigit() else None
    if year is None or not 1888 <= year <= 2100:
        errors.append("L'année doit être un entier entre 1888 et 2100.")

    title = _get(form, "title")
    if not title:
        errors.append("Le titre est obligatoire.")

    director = {"last_name": _get(form, "director_last_name"),
                "first_name": _get(form, "director_first_name")}
    if not director["last_name"]:
        errors.append("Le nom du réalisateur est obligatoire.")

    actors = []
    for last, first in zip(form.getlist("actor_last_name"), form.getlist("actor_first_name")):
        last, first = last.strip(), first.strip()
        if not last and not first:
            continue
        if not last:
            errors.append("Chaque acteur doit avoir un nom.")
        actors.append({"last_name": last, "first_name": first})

    supports = []
    for kind, location in zip(form.getlist("support_type"), form.getlist("support_location")):
        location = location.strip()
        if not location:
            continue
        if kind not in SUPPORT_TYPES:
            errors.append("Type de support inconnu.")
        supports.append({"type": kind, "location": location})

    genres = list(dict.fromkeys(g.strip() for g in _get(form, "genres").split(",") if g.strip()))

    poster_url = _get(form, "poster_url")
    if poster_url and (len(poster_url) > 500 or not URL_RE.match(poster_url)):
        errors.append("L'affiche doit être une adresse web commençant par http:// ou https://.")

    film = {
        "title": title,
        "description": _get(form, "description"),
        "director": director,
        "actors": actors,
        "genres": genres,
        "year": year,
        "supports": supports,
        "poster_url": poster_url,
    }
    return film, errors


def film_to_form(film):
    """Prépare un Film pour préremplir film_form.html."""
    return {
        "title": film.get("title", ""),
        "description": film.get("description", ""),
        "year": film.get("year", ""),
        "director_last_name": film.get("director", {}).get("last_name", ""),
        "director_first_name": film.get("director", {}).get("first_name", ""),
        "genres": ", ".join(film.get("genres", [])),
        "actors": film.get("actors", []),
        "supports": film.get("supports", []),
        "poster_url": film.get("poster_url", ""),
    }


def film_form_from_request(form):
    """Réaffiche le formulaire tel que saisi, après une erreur."""
    film, _ = film_from_form(form)
    data = film_to_form({**film, "year": _get(form, "year")})
    data["genres"] = _get(form, "genres")
    return data


# Redirections

def safe_next(url, default):
    """N'accepte que les chemins internes au site, pour éviter une redirection externe."""
    if url and url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url
    return default