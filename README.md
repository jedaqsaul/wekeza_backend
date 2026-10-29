# Wekeza — Backend API

Wekeza is a small personal finance and expense-tracking application. This
repository is its backend: a Django + Django REST Framework API that a
React (or any other) frontend can consume.

## Features

- Email + password registration and login (JWT-based)
- Record income and expense transactions
- Categorize transactions (income & expense categories, seeded by default)
- Full CRUD on transactions, scoped strictly to the authenticated user
- Filter transactions by type, category, date, or date range; search by description
- Paginated transaction lists
- Backend-calculated financial summary: total income, total expenses,
  balance, transaction count, and category breakdowns
- Recent-transactions endpoint for dashboards
- Consistent JSON error format across the whole API
- Automated test suite covering auth, CRUD, ownership, filtering, and
  dashboard calculations

## Technology stack

- Python 3.11+
- Django 5
- Django REST Framework
- djangorestframework-simplejwt (JWT authentication)
- django-cors-headers
- django-filter
- SQLite for local development / PostgreSQL-ready for production
- python-dotenv for environment configuration

## Project structure

```text
wekeza/
├── manage.py
├── requirements.txt
├── .env.example
├── config/                # project settings, root URLs, WSGI/ASGI, error handler
│   ├── settings.py
│   ├── urls.py
│   ├── exceptions.py
│   ├── wsgi.py
│   └── asgi.py
├── users/                 # custom user model + auth (register/login/me)
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
└── transactions/          # categories, transactions, dashboard summary
    ├── models.py
    ├── serializers.py
    ├── filters.py
    ├── views.py
    ├── urls.py
    ├── signals.py          # seeds default categories after migrate
    ├── admin.py
    └── tests.py
```

## Installation

```bash
# 1. Clone/enter the project
cd wekeza

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# then edit .env — at minimum set a real SECRET_KEY

# 5. Create and apply database migrations
python manage.py makemigrations users transactions
python manage.py migrate

# 6. (optional) create an admin user
python manage.py createsuperuser

# 7. Run the server
python manage.py runserver
```

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | required in production |
| `DEBUG` | `True`/`False` | `False` |
| `ALLOWED_HOSTS` | Comma-separated hostnames | `localhost,127.0.0.1` |
| `DB_NAME` | Postgres DB name — leave blank to use SQLite | *(blank → SQLite)* |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Postgres connection details | — |
| `ACCESS_TOKEN_LIFETIME_MIN` | JWT access token lifetime, minutes | `60` |
| `REFRESH_TOKEN_LIFETIME_DAYS` | JWT refresh token lifetime, days | `7` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins | `http://localhost:3000,http://127.0.0.1:3000` |
| `TIME_ZONE` | Django time zone | `UTC` |

## Database setup

By default (no `DB_NAME` set) the project uses a local SQLite file —
nothing more to configure. To use PostgreSQL instead, create a database
and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` in `.env`.

```bash
python manage.py makemigrations users transactions
python manage.py migrate
```

Default income/expense categories (Salary, Food, Rent, etc.) are seeded
automatically the first time migrations run, via a `post_migrate` signal —
no separate fixture-loading step is required.

Optionally create an admin user:

```bash
python manage.py createsuperuser
```

## Running locally

```bash
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/`.

## Running tests

```bash
python manage.py test
```

This runs the full suite covering registration, authentication,
transaction CRUD, ownership isolation, validation, filtering, and
dashboard calculations.

## Authentication

Wekeza uses JWT (via `djangorestframework-simplejwt`). Register or log in
to receive an `access` and `refresh` token, then send the access token on
every subsequent request:

```
Authorization: Bearer <access_token>
```

Access tokens expire (default 60 min); use the refresh endpoint to obtain
a new one without asking the user to log in again.

## API endpoints

### Auth

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/api/auth/register/` | No | Create an account |
| POST | `/api/auth/login/` | No | Obtain access/refresh tokens |
| POST | `/api/auth/refresh/` | No | Exchange a refresh token for a new access token |
| GET | `/api/auth/me/` | Yes | Get the current user's profile |
| PATCH | `/api/auth/me/` | Yes | Update the current user's profile (name) |

**Register** — `POST /api/auth/register/`

```json
// Request
{ "name": "Jane Doe", "email": "jane@example.com", "password": "StrongPass123" }

// Response 201
{ "id": 1, "name": "Jane Doe", "email": "jane@example.com", "created_at": "2026-08-17T09:00:00Z" }
```

**Login** — `POST /api/auth/login/`

```json
// Request
{ "email": "jane@example.com", "password": "StrongPass123" }

// Response 200
{
  "refresh": "...",
  "access": "...",
  "user": { "id": 1, "name": "Jane Doe", "email": "jane@example.com", "created_at": "..." }
}
```

### Categories

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/categories/` | List all categories. Optional `?type=income` or `?type=expense` |

### Transactions

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/transactions/` | List the user's transactions (paginated, filterable) |
| POST | `/api/transactions/` | Create a transaction |
| GET | `/api/transactions/<id>/` | Retrieve one transaction |
| PUT | `/api/transactions/<id>/` | Replace a transaction |
| PATCH | `/api/transactions/<id>/` | Partially update a transaction |
| DELETE | `/api/transactions/<id>/` | Delete a transaction |
| GET | `/api/transactions/recent/` | Most recent transactions, unpaginated. `?limit=5` (max 50) |

**Query parameters on `GET /api/transactions/`:**

- `type=income` \| `expense`
- `category=<id>`
- `date=YYYY-MM-DD`
- `date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`
- `search=<text>` — matches the description
- `ordering=date` \| `-date` \| `amount` \| `-amount` \| `created_at` \| `-created_at`
- `page=<n>`

**Create transaction** — `POST /api/transactions/`

```json
// Request
{
  "type": "expense",
  "amount": "1500.50",
  "category": 4,
  "description": "Groceries",
  "date": "2026-08-01"
}

// Response 201
{
  "id": 12,
  "type": "expense",
  "amount": "1500.50",
  "category": 4,
  "category_name": "Food",
  "description": "Groceries",
  "date": "2026-08-01",
  "created_at": "2026-08-17T09:00:00Z",
  "updated_at": "2026-08-17T09:00:00Z"
}
```

**List response shape** (paginated):

```json
{
  "count": 42,
  "next": "http://.../api/transactions/?page=2",
  "previous": null,
  "results": [ { "...": "transaction objects" } ]
}
```

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard/summary/` | Financial summary for the current user |

```json
// Response 200
{
  "total_income": "5000.00",
  "total_expenses": "300.00",
  "balance": "4700.00",
  "transaction_count": 3,
  "expenses_by_category": [
    { "category_id": 6, "category": "Food", "total": "200.00" },
    { "category_id": 7, "category": "Transport", "total": "100.00" }
  ],
  "income_by_category": [
    { "category_id": 1, "category": "Salary", "total": "5000.00" }
  ]
}
```

### Error format

Every error response has the same shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "One or more fields failed validation.",
    "details": { "amount": ["Amount must be greater than zero."] }
  }
}
```

## Security notes

- Passwords are hashed by Django's built-in password hashers — never stored
  in plain text.
- All transaction/category/profile endpoints require a valid JWT; queries
  are always scoped to `request.user`, so one user can never read, update,
  or delete another user's data (see `TransactionOwnershipTests`).
- `SECRET_KEY`, database credentials, and CORS origins all come from
  environment variables — nothing sensitive is hardcoded.
- `DEBUG` defaults to `False` and must be explicitly enabled for local dev.
- Django's `AUTH_PASSWORD_VALIDATORS` enforce a minimum-strength password
  on registration.

## Future improvements

- Per-user custom categories (in addition to the shared defaults)
- Recurring transactions
- Multi-currency support
- Budgets and spending alerts
- CSV/Excel export of transactions
- Rate limiting / throttling on auth endpoints
- Refresh-token blacklisting on logout
# wekeza_backend
