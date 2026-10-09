# AcxiomCRM — Flask project

AcxiomCRM is a small Customer Relationship Management (CRM) application. It helps a sales team keep customer details, leads, opportunities and follow-up activities in one place.

The code is divided by task instead of putting the whole website into one Python file.

## Project map

| File or folder | What it does |
|---|---|
| `app.py` | Starts Flask, connects the extensions and registers route groups. |
| `extensions.py` | Creates the database, login and CSRF tools used by the app. |
| `models.py` | Defines the database tables. |
| `validators.py` | Checks email, phone and password formats. |
| `helpers.py` | Keeps common functions such as access checks and audit logging. |
| `routes/auth_routes.py` | Login and logout. |
| `routes/main_routes.py` | Dashboard cards and charts. |
| `routes/customer_routes.py` | Add, edit, list and delete customers. |
| `routes/lead_routes.py` | Add and edit leads; convert a qualified lead. |
| `routes/sales_routes.py` | Opportunities and follow-up activities. |
| `routes/admin_routes.py` | User administration, audit logs and CSV downloads. |
| `routes/api_routes.py` | REST API endpoints. |
| `templates/` | HTML pages shown in the browser. |
| `static/style.css` | Page layout and colours. |
| `seed.py` | Adds example users and CRM records to an empty database. |
| `test_crm.py` | Tests some of the main rules. |

## Run on Windows

Open Command Prompt in this project folder and run:

```bat
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
py -c "import secrets; print(secrets.token_hex(32))"
```

Copy the random value printed by the last command, then set it in the **same Command Prompt window**:

```bat
set SECRET_KEY=paste-your-random-value-here
py run.py
```

Open `http://127.0.0.1:5000` in your browser. If you open a new Command Prompt later, set `SECRET_KEY` again before running the app. Do not commit your real secret key to GitHub.

## Demo accounts

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin@123456` |
| Manager | `manager` | `Manager@123456` |
| Sales Executive | `sales1` | `Sales@123456` |
| Sales Executive | `sales2` | `Sales@123456` |

These are sample credentials for local evaluation only. Do not expose them on a public website.

## Sample CRM data

The fresh database contains customers such as **ABC Technologies**, the lead **Ravi Kumar** from **XYZ Solutions**, and the opportunity **XYZ CRM Project** with a value of **₹3,50,000**. More sample records are included so the dashboard is not empty.

The sample records are created only when the database has no users. If you ran an older project version and want the new sample data, stop the app, back up your database, and then remove `instance\acxiomcrm.db`. Start the app again to create a fresh database. This removes the old local data, so do not do it if you need to keep your records.

## Run the tests

Set `SECRET_KEY` in the current terminal if it is not already set, then run:

```bat
py -m unittest test_crm.py -v
```

## API note

The API login endpoint is `POST /api/v1/auth/login`. After signing in, call `GET /api/v1/csrf-token`. Include the returned token in the `X-CSRFToken` header for API requests that create, update or delete data.

## Important technology note

This project uses **Flask and Flask-Login**. If the evaluator strictly requires **ASP.NET Core Identity** as written in the assignment PDF, Flask-Login is not the same technology. The CRM features may be similar, but this Flask project does not satisfy that specific ASP.NET-only requirement.

This is a learning/demo project. Test it locally and do not store real customer information in it.
