# FlowHub - Metrics API

API FastAPI qui ingère des Issues/PR GitHub, calcule des métriques (lead time, comptes par colonne, stats PR), et stocke des snapshots (PostgreSQL) pour la visualisation de ces données.

La doc complète (APIs GitHub vs API interne, schéma BD, métriques, tests, etc.) est dans le Wiki.

- **Swagger**: http://localhost:8080/docs
- **Wiki** : voir [Wiki](https://github.com/RussellJimmies/metrics-eq15/wiki) du repo

## Aperçu des fonctionnalités

- **API REST complète** avec FastAPI
- **Intégration GitHub** pour la collecte automatique de données
- **Base de donnée** PostgreSQL pour persistance des données de GitHub
- **Métriques Kanban** : lead time, tâches actives, tâches complétées, snapshots
- **Métriques Pull Requests** : lead time, taux de merge, taille, cycles de review
- **Documentation interactive des API** via Swagger UI
- **Tests automatisés** (unitaires et intégration)

## Équipe

- Yan Burton
- William Connolly
- William Lemire

## Prérequis

- **Python 3.11+** (recommandé 3.12)
- **Docker** pour partir PostgreSQL en container
- **Compte GitHub** avec token d'accès **classique**

## 🚀 Démarrage rapide (dev)

### 1) Cloner & installer

```bash
git clone https://github.com/RussellJimmies/metrics-eq15.git
cd metrics-eq15

# Créer un venv et installer les deps
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2) Configurer l’environnement

Créez un fichier `.env` dans src/ (Voir le fichier `.env.example`)

### 3) Démarrer la base (Docker)

```bash
docker compose up db pgadmin
```

- Postgres écoute sur localhost:5432
- (Optionnel) pgAdmin : http://localhost:8082 (config dans `docker-compose.yml`)

### 4) Lancer l’API (FastAPI)

Depuis la racine du repo

```bash
fastapi dev src/app.py
```

- Les tables sont créées automatiquement au démarrage.
- Docs Swagger : http://localhost:8000/docs

## Tests

Le projet inclut deux types de tests :

- **Tests unitaires** : Tests isolés avec mocks et base de données temporaire
- **Tests d'intégration** : Tests end-to-end contre une API en cours d'exécution

### Tests Unitaires

```bash
# Activate .venv
pytest tests/unit/ --cov=src --cov-report=term-missing -v
```

### Tests d'Intégration

Les tests d'intégration nécessitent que l'API soit en cours d'exécution :

```bash
# 1. Démarrer l'API (dans un terminal séparé)
fastapi dev src/app.py

# 2. Exécuter les tests d'intégration (dans un autre terminal)
pytest tests/integration/ --base-url=http://localhost:8000 -v
```

> **Note:** You can run all tests at once (if you started the API like previsouly mentionned for integration tests) using this command:
> ```pytest --cov=src --cov-report=term-missing -v```

**Note pour Windows PowerShell :** Assurez-vous de définir `PYTHONPATH` avant d'exécuter les tests :

```powershell
& .\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
pytest tests/integration/ --base-url=http://localhost:8000 -v
```

### Documentation Complète

Voir la [Documentation des Tests](https://github.com/RussellJimmies/metrics-eq15/wiki/Tests) pour une documentation complète des tests d'intégration.


## Configuration Postman

Un fichier de collection Postman est disponible dans `docs/postman_collection.json` pour faciliter les tests de l'API.

### Import dans Postman

1. Ouvrir Postman
2. Cliquer sur "Import"
3. Sélectionner le fichier `docs/postman_collection.json`
4. Configurer la variable `baseUrl` à `http://127.0.0.1:8000` (ou votre port configuré)

La collection inclut des exemples pour toutes les routes principales avec des paramètres préremplis.

## Technologies utilisées

- **FastAPI** - Framework web moderne et performant pour Python
- **SQLAlchemy** - ORM pour la gestion de base de données
- **Pydantic** - Validation et sérialisation des données
- **pytest** - Framework de tests automatisés
- **Requests** - Client HTTP pour l'API GitHub
- **PostgreSQL** - Bases de données

---

## Comment contribuer

1. Créez un ticket dans le projet, en utilisant un des templates
2. Créez une branche: `90_feat_…` ou `90_fix_…` voir [politique de branches](https://github.com/RussellJimmies/metrics-eq15/wiki/Politique-de-branches)
3. Commitez clairement (Conventional Commits recommandé).
4. Ouvrez une Pull Request en utilisant le template fourni ([.github/pull_request_template.md](.github/pull_request_template.md)).
5. Assurez les tests, la qualité et la mise à jour des docs.

---

## Wiki

Pour plus d'information sur la structure ou le fonctionnement du projet, vuillez consulter notre [wiki](https://github.com/RussellJimmies/metrics-eq15/wiki)
