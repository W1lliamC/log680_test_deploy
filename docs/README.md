# Documentation API Metrics EQ15

## Vue d'ensemble

Cette API permet de collecter et analyser des métriques DevOps pour les tableaux Kanban et les Pull Requests. Elle est conçue pour aider les équipes à mesurer et améliorer leurs processus de développement.

## Architecture

### Structure des données

L'API utilise trois modèles principaux :

1. **Task** : Représente une tâche/issue du tableau Kanban
2. **PullRequest** : Représente une Pull Request GitHub
3. **Snapshot** : Capture l'état du Kanban à un moment donné

### Sources de données

- **GitHub Issues** : Pour les métriques Kanban
- **GitHub Pull Requests** : Pour les métriques de review et merge
- **Labels GitHub** : Pour déterminer les colonnes Kanban

## Métriques disponibles

### Métriques Kanban

| Métrique          | Description                                   | Utilité DevOps                          |
| ----------------- | --------------------------------------------- | --------------------------------------- |
| Lead Time         | Temps entre création et fermeture d'une tâche | Mesurer l'efficacité du flux de travail |
| Tâches Actives    | Nombre de tâches en cours par colonne         | Identifier les goulots d'étranglement   |
| Tâches Complétées | Nombre de tâches terminées                    | Mesurer la vélocité                     |
| Snapshots         | État du tableau à un moment donné             | Analyse historique                      |

### Métriques Pull Requests

| Métrique          | Description                         | Utilité DevOps                              |
| ----------------- | ----------------------------------- | ------------------------------------------- |
| Lead Time PR      | Temps entre création et merge       | Mesurer l'efficacité du processus de review |
| Taux de Merge     | Pourcentage de PRs mergées          | Qualité du code et processus                |
| Taille des PR     | Nombre de lignes modifiées          | Complexité et risque                        |
| Cycles de Review  | Nombre de demandes de modifications | Qualité du code initial                     |
| Latence de Review | Temps avant première review         | Réactivité de l'équipe                      |

## Configuration

### Variables d'environnement requises

```bash
# GitHub API
GITHUB_TOKEN=ghp_...           # Token d'accès GitHub
GITHUB_OWNER=votre-org         # Organisation ou utilisateur
GITHUB_REPO=votre-repo         # Repository

# Mapping Kanban
KANBAN_TODO_LABEL=To Do        # Label pour "À faire"
KANBAN_DOING_LABEL=Doing       # Label pour "En cours"
KANBAN_DONE_LABEL=Done         # Label pour "Terminé"
```

### Base de données

L'API supporte deux types de bases de données :

- **SQLite** (par défaut) : `SQLITE_DSN=sqlite:///./dev.db`
- **PostgreSQL** : `POSTGRES_DSN=postgresql+psycopg2://user:pass@host:5432/db`

## Utilisation

### 1. Initialisation

```bash
POST /init-db
```

Crée les tables nécessaires dans la base de données.

### 2. Ingestion des données

```bash
POST /ingest/refresh
```

Récupère les issues et PRs depuis GitHub et les stocke localement.

### 3. Consultation des métriques

```bash
# Exemples
GET /metrics/kanban/lead-time/123
GET /metrics/prs/merge-rate?start=2024-01-01T00:00:00&end=2024-12-31T23:59:59
```

## Tests

L'API inclut des tests automatisés couvrant :

- **Tests unitaires** : Logique métier
- **Tests d'intégration** : API endpoints
- **Tests de base de données** : Modèles et requêtes

Exécution : `pytest tests/ -v`

## Collection Postman

Le fichier `postman_collection.json` contient :

- Toutes les routes de l'API
- Exemples de paramètres
- Variables d'environnement configurables
- Organisation par catégories (Admin, Kanban, PRs)

### Variables disponibles

- `baseUrl` : URL de l'API (défaut: http://127.0.0.1:8000)
- `startDate` : Date de début pour les requêtes de période
- `endDate` : Date de fin pour les requêtes de période

## Troubleshooting

### Erreurs communes

1. **401 Unauthorized** : Vérifier le `GITHUB_TOKEN`
2. **404 Not Found** : Vérifier `GITHUB_OWNER` et `GITHUB_REPO`
3. **Empty results** : Exécuter `/ingest/refresh` d'abord
4. **Database errors** : Vérifier la configuration de la base de données

### Logs de débogage

Démarrer avec `--log-level debug` pour plus de détails.
