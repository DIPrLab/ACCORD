# ACCORD - Action Constraint-based Conflict Resolution and Detection

![ACCORD Logo](./static/img/accord-logo.png)

ACCORD is a web-based application that seamlessly interfaces with Google Drive to enhance collaboration and conflict resolution in shared resources within an organization. It empowers collaborators by accurately identifying conflicts and recommending suitable resolutions through a user-friendly interface.

## Overview

In a collaborative environment, users sharing resources in cloud services like Google Drive may sometimes perform actions that are in conflict with the expectations of others. ACCORD is designed to address this limitation by monitoring changes in access permissions and the content of the shared resources. It achieves this by using predefined rules known as Action Constraints, which are formulated by users to define permissible actions for others on shared resources.

When ACCORD detects a conflict, it alerts the user who set the action constraints and provides resolution strategies. Unlike native cloud service capabilities, ACCORD goes a step further by tracking file movements, auditing instances where files are moved to non-predefined locations, and monitoring edits to the file, especially outside of given date or time parameters.

## Modules

ACCORD is comprised of three main modules:

1. **Log Extraction Module**: This module acquires and processes activity logs from Google Drive.
   
2. **Conflict Detection Module**: This module includes:
    - **Action Constraints Manager**: Allows users to specify fine-grained permissions on shared resources.
    - **Detection Engine**: Identifies conflicts using data from activity logs and set action constraints.
   
3. **Conflict Resolution Module**: Recommends and executes resolution strategies based on the identified conflicts and involved users. The effectiveness of the resolution strategy depends on various factors such as user permissions, organizational settings, and actions performed post-conflict.

## Directory Structure

The project repository contains the following directories:

- `static/`: Contains subdirectories for different static assets
  - `css/`: Contains CSS stylesheets
  - `img/`: Contains images
  - `js/`: Contains JavaScript files
- `templates/`: Contains HTML template files for the application

## Installation
If using macOS with a brew-installed version of Python, set up and activate a virtual environment first.
### Database
1. Install MySQL using prefered package manager
2. Create a database. Create a file named `db.yaml` in the project root with the following content:
```yaml
mysql_host: localhost
mysql_user: $DB_USERNAME
mysql_password: $DB_PASSWORD
mysql_db: $ACCORD_DB_NAME
```
3. Create tables or initialize database from SQL dump; documentation can be provided upon request. At minimum an administrator account must exist in the `app_users` table
### Google Workspace Credentials & API Tokens
Refer to the [wiki](https://github.com/DIPrLab/ACCORD/wiki/API-Tokens) for token file structure and links to Google Developer Guides
### Dependencies
1. Install Google API Python Client Library 
```bash
$ pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
2. Install Flask
```bash
$ pip install Flask flask-mysqldb
```
3. Install remaining Python libraries
```bash
$ pip install pyyaml psutil
```
## Running ACCORD
ACCORD is a Flask app which can be started with either `$ flask run` or `$ python3 app.py`. Visit `http://127.0.0.1:5000` in a browser. At the login screen, enter the ACCORD credentials for a user registered in the database. The first time you log in for a user, Google will launch a browser window and prompt you to authorize ACCORD's access of their Google account data.
