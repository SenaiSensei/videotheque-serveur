# Vidéothèque : tiers présentation (site web)

Site web de la vidéothèque, en Flask et Jinja2. C'est le tiers présentation de l'application en trois tiers réalisée pour le TP RT0705.

Le site ne stocke aucune donnée : il passe toujours par l'API REST du dépôt [videotheque-api](https://github.com/SenaiSensei/videotheque-api).

## Auteur

**Raphael LABESTE** ([@SenaiSensei](https://github.com/SenaiSensei)) : Master 1 Réseaux et Télécommunications parcours DAS, Université de Reims Champagne-Ardenne.
Projet réalisé dans le cadre du module RT0705 « Programmation des applications en réseau ».

## Description du projet

La vidéothèque est un catalogue de films commun à tous les utilisateurs. Ce site est l'interface utilisée dans le navigateur.

**Pour un utilisateur :**
- inscription, connexion et déconnexion ;
- modification du profil (nom d'utilisateur, mot de passe) et suppression du compte ;
- catalogue en cartes avec affiches, et fiche détaillée de chaque film ;
- catalogue paginé (bandeau Précédent/Suivant, les filtres sont conservés) ;
- recherche par titre, réalisateur, acteur, genre, année ou support (liste déroulante pour le genre et le support) ;
- favoris : une étoile ajoute ou retire un film.

**Pour un administrateur :**
- ajout, modification et suppression des films (acteurs, genres, supports, adresse de l'affiche) ;
- tableau de bord `/admin` : statistiques, liste des films, gestion des comptes (suppression, rôle administrateur).

**Confort :**
- thème clair ou sombre, au choix ou selon le système ;
- bouton pour afficher les mots de passe ;
- notifications.

**Rôle dans l'architecture :**
- **Sessions :** le site gère la session de l'utilisateur dans un cookie signé, `HttpOnly` et `SameSite=Lax`. Elle contient l'identifiant de l'utilisateur et le jeton JWT fourni par l'API.
- **Droits :** le site contrôle les droits avant chaque appel à l'API, et l'API les vérifie à nouveau.
- **Formulaires :** le site les valide, puis construit le JSON envoyé à l'API.
- **Robustesse :** toute action qui modifie des données passe par un formulaire en `POST`, suivi d'une redirection. Les données affichées sont échappées par Jinja. Les scripts JavaScript sont un simple confort : sans eux, le site reste utilisable.
- **Erreurs :** une API injoignable ou trop lente (délai de 5 secondes) affiche une page « Service indisponible ».

## Architecture du projet

### Place dans l'application

L'application est déployée sur trois machines. Seul le pare-feu est joignable depuis l'extérieur :

```
Navigateur ──HTTP :80──> Pare-feu ──> Tiers présentation (ce dépôt)
                         10.11.2.227    10.11.2.225:5000
                             ^                │
                             └──── :5000 ─────┘  HTTP + JSON + jeton JWT
                             │
                             └──> Tiers données (videotheque-api)
                                  10.11.2.226:5000  api ──> mongo
```

- **Le navigateur** ne communique qu'avec le site, par le port 80 du pare-feu.
- **Le site** joint l'API par l'adresse du pare-feu (`API_URL`), jamais directement.
- **Sur cette VM**, le port 5000 n'est accepté que s'il vient du pare-feu.

### Organisation du dépôt

```
videotheque-serveur
├── docker-compose.yml     service presentation, port 5000
├── Dockerfile             image rt0705-presentation (python:3.14-slim)
├── requirements.txt       flask, requests
├── .env.exemple           modèle du fichier .env (non versionné)
├── app.py                 configuration Flask, routes des pages et des actions, erreurs
├── api_client.py          seul point d'accès à l'API (requests, délai, jeton)
├── auth.py                contrôles d'accès : login_required, admin_required, anonymous_required
├── forms.py               validation des formulaires et conversion en JSON
├── static
│   ├── style.css          feuille de style (thèmes clair et sombre)
│   ├── theme.js           choix du thème
│   ├── favorites.js       favoris sans rechargement
│   ├── film_form.js       lignes d'acteurs et de supports
│   ├── password.js        affichage des mots de passe
│   └── menu.js            menu utilisateur
└── templates
    ├── base.html          gabarit commun (barre de navigation, messages)
    ├── _macros.html       carte de film, affiche, étoile, icônes, erreurs
    ├── _users_table.html  tableau des comptes
    ├── login.html, register.html, profile.html
    ├── catalog.html, film.html, favorites.html
    ├── film_form.html, dashboard.html
    └── error.html
```

### Pages

| Route | Page | Droits |
|---|---|---|
| `/login`, `/register` | connexion, inscription | visiteur |
| `/catalog` | catalogue et recherche | connecté |
| `/films/<id>` | fiche d'un film | connecté |
| `/favorites` | mes favoris | connecté |
| `/profile` | mon profil | connecté |
| `/admin/films/new`, `/admin/films/<id>/edit` | formulaire de film | administrateur |
| `/admin` | tableau de bord | administrateur |

## Installation du projet

### Prérequis

- Une machine Linux avec **Docker** et **Docker Compose** (testé sur Ubuntu Server 24.04).
- L'API [videotheque-api](https://github.com/SenaiSensei/videotheque-api) installée et joignable depuis cette machine.
- Ton utilisateur dans le groupe `docker` :
  ```bash
  sudo usermod -aG docker $USER   # puis se reconnecter
  ```

### 1. Récupérer le projet

```bash
git clone https://github.com/SenaiSensei/videotheque-serveur.git
cd videotheque-serveur
```

### 2. Configurer

```bash
cp .env.exemple .env
```

| Variable | Rôle |
|---|---|
| `SECRET_KEY` | clé de signature des cookies de session, par exemple `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `API_URL` | adresse de l'API : `http://10.11.2.227:5000` (par le pare-feu), ou `http://<IP de l'API>:5000` sans pare-feu |

### 3. Lancer le site

```bash
docker compose up -d --build
docker compose exec presentation env | grep API_URL    # vérifier l'adresse de l'API
```

Le site écoute sur le port **5000** de la machine :
- avec le pare-feu : `http://10.11.2.227`, depuis le VPN ;
- sans pare-feu : `http://<IP de la machine>:5000`.

Pour te connecter en administrateur, utilise le compte initial de l'API (`admin@example.org`).

### Mise à jour

Le code est monté dans le conteneur (`/app`), il n'est pas copié dans l'image :
- une modification des templates ou des fichiers statiques s'affiche au rechargement de la page ;
- une modification de `.env` demande `docker compose up -d`, car `restart` ne relit pas `.env` ;
- une modification de `requirements.txt` ou du `Dockerfile` demande `docker compose up -d --build`.

### En cas de problème

| Symptôme | Cause probable |
|---|---|
| Page « Service indisponible » | `API_URL` incorrecte, API arrêtée, ou pare-feu qui bloque. Tester avec `curl -i $API_URL/films`, qui doit renvoyer 401. |
| Redirection vers `/login` à chaque page | Session expirée (1 heure), ou `SECRET_KEY` modifiée. |
| `network ... declared as external, but could not be found` | Ancienne configuration à un seul hôte : retirer le réseau `rt0705-presentation-net` du `docker-compose.yml`. |