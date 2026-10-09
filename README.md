# \# AcxiomCRM

# 

# AcxiomCRM is a simple Customer Relationship Management application built using Python and Flask. It helps a sales team manage customers, leads, opportunities and follow-up activities.

# 

# \## Features

# 

# \- User login and role-based access

# \- Customer and lead management

# \- Opportunity and follow-up management

# \- Dashboard with charts and summaries

# \- User management and audit logs

# \- CSV reports and REST API

# \- Input validation and CSRF protection

# 

# \## Technologies Used

# 

# Python, Flask, SQLite, HTML, CSS and JavaScript.

# 

# \## Project Structure

# 

# \- `app.py` - Flask application setup

# \- `models.py` - Database tables

# \- `routes/` - Application pages and API routes

# \- `templates/` - HTML pages

# \- `static/` - CSS files

# \- `validators.py` - Input validation

# \- `helpers.py` - Common functions

# \- `seed.py` - Sample data

# \- `run.py` - Runs the application

# \- `test\_crm.py` - Automated tests

# 

# \## How to Run

# 

# Clone the repository:

# 

# ```bash

# git clone https://github.com/dineshyadav16/AcxiomCRM.git

# cd AcxiomCRM

# ```

# 

# Create a virtual environment and install the packages:

# 

# ```bat

# py -m venv venv

# venv\\Scripts\\activate

# py -m pip install -r requirements.txt

# ```

# 

# Generate a secret key:

# 

# ```bat

# py -c "import secrets; print(secrets.token\_hex(32))"

# ```

# 

# Set the generated value in the same Command Prompt:

# 

# ```bat

# set SECRET\_KEY=paste-your-key-here

# ```

# 

# Start the application:

# 

# ```bat

# py run.py

# ```

# 

# Open http://127.0.0.1:5000 in your browser.

# 

# \## Running Tests

# 

# ```bat

# py test\_crm.py

# ```

# 

# \## Sample Data

# 

# The project includes sample customers, leads and opportunities for testing. For example, ABC Technologies and the XYZ CRM Project worth ₹3,50,000.

# 

# \## Note

# 

# This project was developed for learning and demonstration. Do not use demo credentials or store real customer information in a public deployment. Keep your secret key private.

