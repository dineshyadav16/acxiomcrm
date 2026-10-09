# AcxiomCRM — explanation guide

Use this guide to understand the code and describe it in your own words. You do not need to memorise every line. Start by learning what each file is responsible for.

## 1. How the website works

The basic flow is:

1. The user opens a page in the browser.
2. Flask finds the matching route in the `routes` folder.
3. The route reads the form values and checks them.
4. SQLAlchemy reads or saves the data in the database.
5. Flask returns an HTML page from `templates`, or JSON for an API request.

## 2. What the main files mean

**`app.py` — starts the application**

It sets the secret key and database settings, connects Flask extensions, then registers the route groups. The page code is in other files, so this file stays short.

**`models.py` — database tables**

A model is a Python class that represents a database table. `Customer` stores customer details; `Lead` stores possible customers; `Opportunity` stores possible sales; `FollowUp` stores scheduled contact; `User` stores login details and roles; `AuditLog` records important actions.

**`validators.py` — input checks**

These functions check that an email and phone number have an acceptable format and that a password contains the required character types. They return a result for the route to use.

**`helpers.py` — shared functions**

`log_audit()` saves an action to the audit table. `role_required()` restricts pages by role. The `visible_...()` functions filter records so a Sales Executive normally sees their own assigned work.

**`routes/` — what happens when a URL is opened**

Each file handles one area. For example, `customer_routes.py` has the customer pages; `lead_routes.py` has lead pages; and `api_routes.py` handles JSON requests.

**`templates/` and `static/style.css` — user interface**

The templates contain the HTML. The CSS controls spacing, colours, tables, forms and the responsive layout. This keeps presentation code separate from Python logic.

## 3. Login in simple terms

1. The user enters a username or email and a password.
2. The app looks up the user in the database.
3. Werkzeug checks the entered password against its stored hash. The plain-text password is not stored.
4. After repeated incorrect passwords, the account is locked temporarily.
5. Flask-Login remembers that the user has signed in.
6. Routes check the user's role and record ownership before showing or changing data.

## 4. Roles

- **Admin:** can manage user accounts and open administration pages.
- **Manager:** can view reports and audit logs, and can access team records.
- **Sales Executive:** mainly works with records assigned to that user.

## 5. What the dashboard shows

- Total customers
- Open leads
- Open opportunities
- Planned follow-ups
- Pipeline value and weighted pipeline value
- Charts for lead status, opportunity stages and monthly won-opportunity values

The monthly chart uses the opportunity's creation date as a simple demonstration. It is not an accounting report based on the actual date a deal was closed.

## 6. A simple explanation for a project review

“My project is a CRM application built with Flask. It stores customers, leads, opportunities, follow-up activities and user details in a database. I used separate Python files for database models, input validation, common functions and routes. The user signs in, and the application checks their role before allowing access. It also records important activity in an audit log. The dashboard shows summary figures and charts, and the REST API returns JSON for other applications.”

Only use this explanation after you have run the project and practised explaining the parts you understand.

## 7. Current limits to be aware of

- The assignment PDF mentions ASP.NET Core Identity. This project uses Flask-Login instead, so it does not meet that exact technology requirement if it is mandatory.
- CSV downloads are currently provided for customers, leads and opportunities. Other report types from the assignment would need to be added.
- The demo usernames and passwords are not suitable for a public production system.
