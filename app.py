from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
import yaml, hashlib, os, time, random, re
from datetime import datetime
from math import floor
from functools import wraps
from serviceAPI import create_user_driveAPI_service, create_directoryAPI_service, create_reportsAPI_service
from detection import get_filteroptions
from conflictDetctionAlgorithm import detectmain
from sqlconnector import DatabaseQuery
from activitylogs import Logupdater
from demosimulator import UserSubject, PerformActions
from logextraction import extractDriveLog
from executeResolutions import ExecuteResolutionThread


# Dictionary to store the user services
user_services = {}

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load database configuration
db_config = yaml.load(open('db.yaml'), Loader=yaml.SafeLoader)
app.config['MYSQL_HOST'] = db_config['mysql_host']
app.config['MYSQL_USER'] = db_config['mysql_user']
app.config['MYSQL_PASSWORD'] = db_config['mysql_password']
app.config['MYSQL_DB'] = db_config['mysql_db']

mysql = MySQL(app)

def simplify_datetime(datetime_str):
    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    formatted_date = dt.strftime("%d %B %Y, %H:%M:%S")
    return formatted_date

def process_logs(logV):
    '''Generate a human-readable string from an activity log'''
    action = logV[1][:3]  # Get the first three characters for comparison
    actor = logV[5].split('@')[0].capitalize()

    if action == "Cre":
        return f'{actor} has Created a resource'
    elif action == "Del":
        return f'{actor} has Deleted a resource'
    elif action == "Edi":
        return f'{actor} has Edited a resource'
    elif action == "Ren":
        return f'{actor} has Renamed a resource'
    elif action == "Mov":
        _, src, dest = logV[1].split(':')
        return f'{actor} has Moved a resource from {src} to {dest}'
    elif action == "Per":
        sub_parts = logV[1].split(':')
        first_sub_part = sub_parts[1].split('-')[0] if len(sub_parts) > 1 else ""
        second_sub_part = sub_parts[2].split('-')[0] if len(sub_parts) > 2 else ""
        user = sub_parts[3].split('@')[0].capitalize() if len(sub_parts) > 3 else ""
        permissions = { 'can_edit': '"Editor"',
                        'can_comment,can_view': '"Commenter"',
                        'can_view,can_comment': '"Commenter"',
                        'can_view': '"Viewer"',
                        'owner': '"Owner"' }
        if second_sub_part == "none":
            return f'{actor} has given {user} {permissions.get(first_sub_part)} permissions'
        elif first_sub_part == "none":
            return f'{actor} has removed {permissions.get(second_sub_part)} permissions for {user}'
        else:
            return f'{actor} has updated permissions for {user} from {permissions.get(second_sub_part)} to {permissions.get(first_sub_part)}'
    else:
        return " ".join(logV)

## Route to ensure there is no going back and cache is cleared
@app.after_request
def add_no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response

@app.before_request
def before_request():
    if 'user_id' in session:
        if request.endpoint in ['login']:
            if session['user_role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))

# User management routes
@app.route('/', methods=['GET', 'POST'])
def login():
    '''Index: login page'''
    session.clear()
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        password = hashlib.md5(password.encode())

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT email,password,role FROM app_users WHERE email=%s AND password=%s", (email, password.hexdigest()))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            session['user_role'] = user[2]
            session['username'] = user[0].split('@')[0]  # Store the username in the session

            # Create the drive API and directory API service after a successful login
            drive_service = create_user_driveAPI_service(session['username'])
            directory_service = create_directoryAPI_service()
            reportsAPI_service = create_reportsAPI_service()

            # Store services in the global services dictionary
            user_services[session['username']] = {'drive': drive_service, 'directory': directory_service, 'reports': reportsAPI_service}

            # Fetch and Update the logs database
            activity_logs = Logupdater(mysql, user_services[session['username']]['reports'])
            activity_logs.updateLogs_database() 
            del activity_logs

            if session['user_role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            error = "Invalid email or password."

    return render_template('index.html', error=error)

@app.route('/register_user', methods=['POST'])
def register_user():
    '''Register a new user and insert into database'''
    data = request.get_json()

    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    role = data.get('role')

    password = hashlib.md5(password.encode())

    # Server-side email format validation
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    if not email_pattern.match(email):
        return jsonify({"message": "Invalid email format"})

    # If the email is valid, proceed with saving the user to your database, etc.
    cursor = mysql.connection.cursor()

    # Check if email already exists in the database
    email_check_query = "SELECT email FROM app_users WHERE email=%s"
    cursor.execute(email_check_query, (email,))
    existing_email = cursor.fetchone()

    # Email already exists, return an error
    if existing_email:
        return jsonify({"message": "Email already in use"})

    # Insert a new user into the app_users table
    query = "INSERT INTO app_users (name, email, password, role) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (username, email, password.hexdigest(), role))

    # Commit changes
    mysql.connection.commit()

    return jsonify({"message": "User registered successfully"})

@app.route('/logout')
def logout():
    '''Delete user session to log out user'''
    # Remove services from the global services dictionary upon logout
    if 'username' in session:
        user_services.pop(session['username'], None)

    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# Routes for user and Admin Dashboards
@app.route('/admin_dashboard')
def admin_dashboard():
    '''Administrator (privileged) dashboard'''
    if 'user_id' in session and session['user_role'] == 'admin':

        drive_service = user_services[session['username']]['drive']
        directory_service = user_services[session['username']]['directory']

        options_actor, options_document = get_filteroptions(drive_service, directory_service)
        session['user_documents'] = options_document

        return render_template('dashboard.html', user_role='admin', username=session['username'], options_actor=options_actor, options_document=options_document)
    else:
        return redirect(url_for('login'))

@app.route('/user_dashboard')
def user_dashboard():
    '''User dashboard'''
    if 'user_id' in session and session['user_role'] != 'admin':

        drive_service = user_services[session['username']]['drive']
        directory_service = user_services[session['username']]['directory']
        options_actor, options_document = get_filteroptions(drive_service, directory_service)
        session['user_documents'] = options_document

        return render_template('dashboard.html', user_role='user', username=session['username'], options_actor=options_actor, options_document=options_document)
    else:
        return redirect(url_for('login'))

# Routes for activity logs
@app.route('/refresh_logs', methods=['POST'])
def refresh_logs():
    '''Fetch activity logs & update database. Returns number of logs in response'''
    # Fetch and Update the logs database
    activity_logs = Logupdater(mysql, user_services[session['username']]['reports'])
    total_logs = activity_logs.updateLogs_database() 
    del activity_logs

    return jsonify(len=str(total_logs))

# Routes for conflict detection
@app.route('/detect_conflicts_demo', methods=['POST'])
def detect_conflicts_demo():
    '''Detect function for demo: Detect conflicts in logs since 'current_date''''
    currentDateTime = request.form.get('current_date')

    # Extract Logs from databse with the filter parameters and also extract all the action constraints
    db = DatabaseQuery(mysql.connection, mysql.connection.cursor())
    logs = db.extract_logs_date(currentDateTime)
    actionConstraintsList = db.extract_action_constraints("LIKE '%'")
    del db

    # Create a Dictionary of action constraitns with key as documentID
    actionConstraints = {}
    for constraint in actionConstraintsList:
        if(constraint[1] not in actionConstraints):
            actionConstraints[constraint[1]] = [constraint]
        else:
            actionConstraints[constraint[1]].append(constraint)

    conflictID = []
    if(logs != None and len(logs)>1):
        
        # Initializing and setting user view parameters
        headers = logs.pop(0)
        conflictLogs = []
        logs = logs[::-1]

        # Calculate time taken by the detection Engine to detect conflicts
        T0 = time.time()
        result = detectmain(logs,actionConstraints)
        T1 = time.time()

        # Update the display table only with Conflicts and print the detection Time
        totalLogs = len(result)
        conflictsCount = 0
        briefLogs = []
        db = DatabaseQuery(mysql.connection, mysql.connection.cursor())

        # Extract only the logs that have a conflict
        for i in range(totalLogs):
            if(result[i]):
                event = logs[i]
                conflictLogs.append([simplify_datetime(event[0]),event[1].split(':')[0].split('-')[0],event[3],event[5].split('@')[0].capitalize()])
                briefLogs.append(event)
                conflictsCount += 1
                conflictID.append(str(totalLogs - i))

                # Add conflicts to the conflicts table to track resolved conflicts
                db.add_conflict_resolution(event[0], event[1])

        del db

        if(T1 == T0):
            speed = "Inf"
        else:
            speed = floor(conflictsCount/(T1-T0))

        detectTimeLabel = "Time taken to detect "+str(conflictsCount)+" conflicts from "+str(totalLogs)+" activity logs: "+str(round(T1-T0,3))+" seconds. Speed = "+str(speed)+" conflicts/sec"

        return jsonify(logs=conflictLogs, detectTimeLabel=detectTimeLabel, briefLogs=briefLogs, conflictID = conflictID)
    
    else:
        detectTimeLabel = "No Activites Found for the selected filters"
        return jsonify(logs=[], detectTimeLabel=detectTimeLabel, briefLogs=[], conflictID = conflictID)

# Routes for Action Simulator
@app.route('/simulate_actions', methods=['POST'])
def simulate_actions():
    '''Randomly generate user actions for Simulator without performing them

    Request JSON:
        conflictAction: str, ensure this action is an option
        num_users: int, number of users in simulation, including admin
        num_actions: actions to generate

    Response: list of JSON objects for each action with keys:
        "performingUser", "action", "targetUser", "fileName", and "fileID"
    '''
    data = request.json
    conflict_action = data['conflictAction']
    num_users = int(data['numUsers'])
    num_actions = int(data['numActions'])

    # Fetch the List of users
    directory = "tokens/"
    file_dict = {}
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            key = filename.split("_")[1].split(".")[0]+'@accord.foundation'
            file_dict[key] = filename

    ##  Perform Action Simulats based on number of users selected and number of actions
    # Ensure admin is included
    selected_users = ['admin@accord.foundation']
    other_users = list(file_dict.keys())
    other_users.remove('admin@accord.foundation')

    # Choose additional users randomly if needed
    if num_users > 1:
        selected_users.extend(random.sample(other_users, num_users - 1))

    actions = ['Add Permission', 'Remove Permission', 'UpdatePermission', 'Edit', 'Move', 'Delete']
    file_users = ['admin@accord.foundation']
    action_log = []
    performed_actions = 0

    # Fetch the file Id and File Name
    owner = UserSubject(session['user_id'], file_dict)
    files = owner.fetch_file()
    file_name = random.choice(list(files.keys()))
    file_id = files[file_name]

    # Randomly construct actions
    while performed_actions < num_actions:
        performing_user = random.choice(file_users)
        possible_actions = actions.copy()

        if 'Delete' in possible_actions and performed_actions != num_actions - 1:
            possible_actions.remove('Delete')  # Delete can only be the last action

        if conflict_action not in possible_actions:
            possible_actions.append(conflict_action)

        selected_action = random.choice(possible_actions)

        target_user = random.choice(file_users)
        if selected_action == 'Remove Permission':
            if len(file_users) > 1 and target_user != performing_user and target_user != 'admin@accord.foundation':
                file_users.remove(target_user)
                action_log.append({
                    "performingUser": performing_user,
                    "action": selected_action,
                    "targetUser": target_user,
                    "fileName": file_name,
                    "fileID": file_id})
                performed_actions += 1
        elif selected_action == 'Add Permission':
            non_file_users = list(set(selected_users) - set(file_users))
            if non_file_users:
                new_user = random.choice(non_file_users)
                file_users.append(new_user)
                action_log.append({
                    "performingUser": performing_user,
                    "action": selected_action,
                    "targetUser": new_user,
                    "fileName": file_name,
                    "fileID": file_id})
                performed_actions += 1
        elif selected_action == 'Update Permission':
            if len(file_users) > 1 and target_user != performing_user and target_user != 'admin@accord.foundation':
                action_log.append({
                    "performingUser": performing_user,
                    "action": selected_action,
                    "targetUser": target_user,
                    "fileName": file_name,
                    "fileID": file_id})
                performed_actions += 1
        elif selected_action in ['Edit', 'Move']:
            action_log.append({
                    "performingUser": performing_user,
                    "action": selected_action,
                    "targetUser": "-",
                    "fileName": file_name,
                    "fileID": file_id})
            performed_actions += 1
        elif selected_action == 'Delete' and conflict_action == 'Delete' and performed_actions == num_actions - 1:
            action_log.append({
                    "performingUser": performing_user,
                    "action": selected_action,
                    "targetUser": "-",
                    "fileName": file_name,
                    "fileID": file_id})
            performed_actions += 1

    return jsonify({'success': True, 'actions': action_log})

@app.route('/fetch_task_content', methods=['POST'])
def fetch_task_content():
    '''Simulator: Perform appropriate action on Drive resources

    Request:
        action: str
        addConstraint: unknown, not used
        constraintType: str
        fileID: str
        actionIndex: int, actions already performed (this is nth action)
    '''
    # Extract JSON data from POST request
    data = request.get_json()
    action = data['action']
    addConstraint = data['addConstraint']
    constraintType = data['constraintType']
        actionIndex = int(data['actionIndex'])
    fileID = data['fileID']
    if(fileID == 'None'):
        fileID = None

    #### Create Simulator Object and Execute Actions #########
    # Extract User tokes 
    directory = "tokens/"
    file_dict = {}
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            key = filename.split("_")[1].split(".")[0]+'@accord.foundation'
            file_dict[key] = filename

    ### Perform first few actions as owner and remainer other actions as other ditors
    owner = UserSubject(session['user_id'], file_dict)

    if(actionIndex < 2):
        actor = owner
    else:
        if(fileID != 'None'):
            # get all the editors of the file
            file = owner.service.files().get(fileId=fileID, fields="permissions").execute()
            email_list = []  # Create an empty list to store the emails
            for permission in file['permissions']:
                if permission.get('role') in ['writer', 'owner']:
                    email_list.append(permission.get('emailAddress'))  # Add email to the list if user has 'writer' or 'owner' permission

            # Remove the owner's email from the list if it exists
            if owner.userEmail in email_list:
                email_list.remove(owner.userEmail)

            # Select a random email from the list
            actorEmail = random.choice(email_list) if email_list else owner.userEmail
            actor = UserSubject(actorEmail, file_dict)
        else:
            actor = owner

    # Add Constraint and Perform the constraint action 
    if(actionIndex == 3):
        db = DatabaseQuery(mysql.connection, mysql.connection.cursor())
        file = owner.service.files().get(fileId=fileID, fields='name').execute()
        document_name = file['name']

        if(action == "Edit" and constraintType == "Time Limit Edit"):
            current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            constraints = [document_name, fileID, action, constraintType, actor.userEmail, "TRUE", "lt",owner.userEmail, current_datetime]
        else:
            constraints = [document_name, fileID, action, constraintType, actor.userEmail, "FALSE", "eq", owner.userEmail, '-']
        db.add_action_constraint(constraints)

        owner_userName = owner.userName.split('@')[0].capitalize()
        actor_userName = actor.userName.split('@')[0].capitalize()

        ## Creating the constraint message
        constraint = ""

        if action == "Permission Change":
            if constraintType == "Add Permission":
                constraint = f'<span style="color:black">User:</span> <span style="color:red">{owner_userName}</span> has restricted <span style="color:black">Target:</span> <span style="color:red">{actor_userName}</span> from <span style="color:black">Action Type:</span> <span style="color:red">adding new users</span> to <span style="color:black">Resource:</span> <span style="color:red">{document_name}</span>'
            elif constraintType == "Remove Permission":
                constraint = f'<span style="color:black">User:</span> <span style="color:red">{owner_userName}</span> has restricted <span style="color:black">Target:</span> <span style="color:red">{actor_userName}</span> from <span style="color:black">Action Type:</span> <span style="color:red">removing users</span> from <span style="color:black">Resource:</span> <span style="color:red">{document_name}</span>'
            else:
                constraint = f'<span style="color:black">User:</span> <span style="color:red">{owner_userName}</span> has restricted <span style="color:black">Target:</span> <span style="color:red">{actor_userName}</span> from <span style="color:black">Action Type:</span> <span style="color:red">modifying users permission</span> of <span style="color:black">Resource:</span> <span style="color:red">{document_name}</span>'

        elif action == "Edit":
            if constraintType == "Can Edit":
                constraint = f'{owner_userName} has set a constraint on {document_name} for user {actor_userName} from editing the resource'
            else:
                constraint = f'{owner_userName} has set a constraint on {document_name} for user {actor_userName} from editing the resource out of timeframe'

        elif action == "Move":
            constraint = f'{owner_userName} has set a constraint on {document_name} for user {actor_userName} from moving the resource'

        elif action == "Delete":
            constraint = f'{owner_userName} has set a constraint on {document_name} for user {actor_userName} from deleting the resource'

        else:
            constraint = f'{owner_userName} has set a constraint on {document_name} for user {actor_userName} from creating additional resources'

        time.sleep(3)

    Simulator = PerformActions(owner, actor, action, constraintType, fileID, actionIndex, addConstraint)
    fileID = Simulator.perform_actions(file_dict)

    # Build a dictionary with fileID and constraint created
    response_data = {
        'fileID': fileID,
        'constraint': constraint
    }

    # Return file ID and the constraint
    return jsonify(response_data)

# Routes for Action Constraints
@app.route('/addActionConstraints', methods=['POST'])
def add_action_constraints():
    '''Add action constraint to database with Admin as owner'''
    data = request.json
    actions = data['actions']
    try:
        for action in actions:
            file_name = action['fileName']
            file_id = action['fileID']
            target_user = action['performingUser']
            action_type = action['action']
            owner = 'admin@accord.foundation'  # Assuming the owner

            # Define the constraint action and type based on the action
            if action_type in ['Add Permission', 'Remove Permission', 'Update Permission']:
                constraint_action = 'Permission Change'
                constraint_type = action_type
            elif action_type == 'Move':
                constraint_action = 'Move'
                constraint_type = 'Can Move'
            elif action_type == 'Edit':
                constraint_action = 'Edit'
                constraint_type = 'Can Edit'
            elif action_type == 'Delete':
                constraint_action = 'Delete'
                constraint_type = 'Can Delete'
            else:
                continue  # Skip unknown action types

            # Example: This is where you would call your database method
            constraints = [file_name, file_id, constraint_action, constraint_type, target_user, "FALSE", "eq", owner, '-']
            
            # Adding constraint to the databse
            db = DatabaseQuery(mysql.connection, mysql.connection.cursor())
            db.add_action_constraint(constraints)  
            del db

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/fetch_actionConstraints', methods=['POST'])
def fetch_action_constraints():
    '''Fetch actions constraints created today and return JSON object for each'''
    db = DatabaseQuery(mysql.connection, mysql.connection.cursor())
    constraints = db.fetch_action_constraints()

    ## Process the constraints and create a dictionary
    processed_constraints = []  # List to hold all processed constraints dictionaries

    # Iterate over each constraint skipping the header
    for constraint in constraints[1:]:

        # Unpack each constraint row into variables
        doc_name, doc_id, action, action_type, constraint_target, action_value, comparator, constraint_owner, allowed_value, time_stamp = constraint

        # Initialize the dictionary to store the processed constraint
        constraint_dict = {
            "TimeStamp": time_stamp,
            "ConstraintOwner": constraint_owner,
            "ConstraintTarget": constraint_target,
            "File": doc_name
        }

        # Determine the Constraint value based on Action Value and Action Type
        if action_value == "FALSE":
            if action_type == "Add Permission":
                constraint_value = "Cannot Add users"
            elif action_type == "Remove Permission":
                constraint_value = "Cannot Remove users"
            elif action_type == "Update Permission":
                constraint_value = "Cannot Update user Permissions"
            elif action_type == "Can Move":
                constraint_value = "Cannot Move file"
            elif action_type == "Can Delete":
                constraint_value = "Cannot Delete the file"
            elif action_type == "Can Edit":
                constraint_value = "Cannot Edit file"
            else:
                constraint_value = "Undefined Action"  # Default message if no specific action type matched
        else:
            constraint_value = "No restriction"  # Default message if action value is not "FALSE"

        # Set the 'Constraint' key in the dictionary
        constraint_dict['Constraint'] = constraint_value

        # Append the constructed dictionary to the list
        processed_constraints.append(constraint_dict)

    return jsonify(processed_constraints)

############## Route to fetch Drive Log ##########################
@app.route('/fetch_drive_log', methods=['GET'])
def fetch_drive_log():
    '''Fetch activity logs since specified time.'''
    startTime = request.args.get('time') # retrieve time from the GET parameters
    # Create DB connection
    db = DatabaseQuery(mysql.connection, mysql.connection.cursor())

    totalLogs = []

    if(startTime != None):
        # Extract the activity logs from the Google cloud from lastlog Date
        activity_logs = extractDriveLog(startTime, user_services[session['username']]['reports'])

        # Update the log Database table when the new activities are recorded
        if(len(activity_logs) > 1):
            activity_logs.pop(0)
            for logitem in reversed(activity_logs):
                logV = logitem.split('\t*\t')
                totalLogs.append({'time':simplify_datetime(logV[0]), 'activity':process_logs(logV), 'actor': logV[5].split('@')[0].capitalize(), 'resource':logV[3]})

    del db
    return jsonify(totalLogs)

####### Route for fetching Action Constraints ###############
@app.route('/get_action_constraints', methods=['POST'])
def get_action_constraints():
    '''Fetch action constraints by doc id, action, and target'''
    doc_id = request.form.get('doc_id')
    action = request.form.get('action')
    action = action.split(':')[0].split('-')[0]
    action_type = request.form.get('action_type')
    constraint_target = request.form.get('constraint_target')

    db = DatabaseQuery(mysql.connection, mysql.connection.cursor())
    constraints = db.extract_targetaction_constraints(doc_id, action, action_type, constraint_target)
    if(len(constraints) > 0):
        return jsonify(constraints)
    else:
        return jsonify([])

# Routes for Conflict Resolution
@app.route('/fetch_resolutions', methods=['POST'])
def fetch_resolutions():
    '''Fetch resuolutions by conflict action, actor, doc id, user, and time'''
    action = request.form.get('action').split(':')[0].split('-')[0]
    actor = request.form.get('actor')
    document_id = request.form.get('document_id')
    current_user = request.form.get('current_user')
    conflictTime = request.form.get('activity_time')

    # Extract conflict and resolution from database
    db = DatabaseQuery(mysql.connection, mysql.connection.cursor())
    resolutions = db.get_conflict_resolutions(action)
    val = db.extract_conflict_resolution(conflictTime, request.form.get('action'))
    del db

    if resolutions:
        return jsonify(resolutions=resolutions, resolved = val)
    else:
        return jsonify(resolutions=[], resolved = "False")

@app.route('/execute_resolution', methods=['POST'])
def execute_resolution():
    '''Execute resolution and mark conflict as resolved in database'''
    try:
        # Retrieve the data sent in the POST request
        activityTime = request.form.get('activityTime')
        documentId = request.form.get('documentId')
        action = request.form.get('action')
        actor = request.form.get('actor')
        drive_service = user_services[session['username']]['drive']

        er = ExecuteResolutionThread(activityTime, action, documentId, actor, drive_service)
        er_status = er.run()
        if(er_status):
            print("Execution success")
            db = DatabaseQuery(mysql.connection, mysql.connection.cursor())
            db.update_conflict_resolution(activityTime, action, "True")
            del db
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'failure'}), 500

    except Exception as e:
        # Log the error and return an error response
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
