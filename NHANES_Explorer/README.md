# NHANES Variable Explorer

A Django app for searching the NHANES codebook artifact using TF-IDF semantic
search, viewing full variable detail pages, and saving variables to a
persistent favorites library.

---

## Requirements

- Python 3.11+
- The completed `nhanes_codebook_artifact.csv` from Phase 1

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Point the app at your artifact CSV

Open `nhanes_explorer/settings.py` and set `NHANES_ARTIFACT_PATH` to the
absolute path of your combined artifact file:

```python
NHANES_ARTIFACT_PATH = '/path/to/nhanes_codebook_artifact.csv'
```

Or a path relative to the project root:

```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
NHANES_ARTIFACT_PATH = BASE_DIR / 'nhanes_codebook_artifact.csv'
```

### 3. Run database migrations

```bash
python manage.py migrate
```

This creates the SQLite database and the `Favorite` table.

### 4. (Optional) Create an admin superuser

```bash
python manage.py createsuperuser
```

The Django admin at `/admin/` lets you inspect and manage saved favorites.

### 5. Start the development server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser.

---

## Pages

| URL                         | Description                              |
|-----------------------------|------------------------------------------|
| `/`                         | Search page                              |
| `/variable/<COLUMN_NAME>/`  | Full detail page for a single variable   |
| `/library/`                 | Saved favorites library                  |
| `/admin/`                   | Django admin                             |

---

## How search works

On the first search query, the app loads the artifact CSV and builds a
TF-IDF index across all text fields for every variable. The index is cached
in memory for the lifetime of the process -- subsequent searches are
near-instant.

Scoring combines:
- **70% TF-IDF cosine similarity** across column_name, sas_label,
  description, component, data_file, human_readable, and value_label text
- **30% fuzzy partial match** on column_name, sas_label, and human_readable

The search engine considers unigrams and bigrams, so queries like
"blood pressure" or "fasting glucose" work as phrases.

---

## Project structure

```
nhanes_explorer/
├── manage.py
├── requirements.txt
├── nhanes_codebook_artifact.csv   ← place your artifact here (or update path)
├── nhanes_explorer/
│   ├── settings.py                ← set NHANES_ARTIFACT_PATH here
│   ├── urls.py
│   └── wsgi.py
└── varSearch/
    ├── models.py                  ← Favorite model (SQLite)
    ├── search_engine.py           ← TF-IDF index and search()
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── migrations/
    └── templates/varSearch/
        ├── base.html
        ├── search.html
        ├── detail.html
        ├── library.html
        └── 404.html
```

---

## Rebuilding the search index

The index is rebuilt automatically whenever the Django process restarts.
If you update the artifact CSV, restart the server and the new index will
be loaded on the next search request.

To force a reload without restarting, call this from a Django shell:

```python
from varSearch.search_engine import _get_index
_get_index.cache_clear()
```

---

## Production notes

- Set `DEBUG = False` and a strong `SECRET_KEY` in `settings.py`
- Set `ALLOWED_HOSTS` to your domain
- Run with `gunicorn nhanes_explorer.wsgi` behind nginx
- Consider using PostgreSQL instead of SQLite for the favorites database
