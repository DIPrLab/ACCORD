from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def get_creds(SCOPES, filename):
    '''Initialize Credentials from file

    Args:
        SCOPES: str, OAuth 2.0 scopes URI specifying app, data, & access level
        filename: str, JSON tokens file relative path

    Returns: google.oauth2.credentials.Credentials
    '''
    try:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is created after first time
        if os.path.exists(filename):
            creds = Credentials.from_authorized_user_file(filename, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(filename, 'w') as token:
                token.write(creds.to_json())
        
        return creds

    except LookupError as le:
        return "Error in the key or index !!\n" + str(le)
    except ValueError as ve:
        return "Error in Value Entered !!\n" + str(ve)
    except OSError as oe:
        return "Error! " + str(oe)


def create_reportsAPI_service():
    '''Create Admin Reports API v1 service with admin's credentials'''
    try:
        # If modifying these scopes, delete the file token.json.
        SCOPES = ['https://www.googleapis.com/auth/admin.reports.audit.readonly']
        creds = get_creds(SCOPES, 'token.json')
        service = build('admin', 'reports_v1', credentials=creds)
        return service

    except LookupError as le:
        return "Error in the key or index !!\n" + str(le)
    except ValueError as ve:
        return "Error in Value Entered !!\n" + str(ve)
    except OSError as oe:
        return "Error! " + str(oe)

def create_driveAPI_service():
    '''Create Drive API v3 service with admin's credentials'''
    try:
        # If modifying these scopes, delete the file token.json.
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = get_creds(SCOPES, 'token_drive.json')
        service = build('drive', 'v3', credentials=creds)
        return service

    except LookupError as le:
        return "Error in the key or index !!\n" + str(le)
    except ValueError as ve:
        return "Error in Value Entered !!\n" + str(ve)
    except OSError as oe:
        return "Error! " + str(oe)

def create_user_driveAPI_service(user_token_name):
    '''Create Drive API v3 service with user's credentials'''
    try:
        user_token_name = 'token_'+user_token_name+'.json'
        # If modifying these scopes, delete the file token.json.
        SCOPES = ['https://www.googleapis.com/auth/drive']
        user_token_name = 'tokens/' + user_token_name
        creds = get_creds(SCOPES, user_token_name)
        service = build('drive', 'v3', credentials=creds)
        return service

    except LookupError as le:
        return "Error in the key or index !!\n" + str(le)
    except ValueError as ve:
        return "Error in Value Entered !!\n" + str(ve)
    except OSError as oe:
        return "Error! " + str(oe)

def create_directoryAPI_service():
    '''Create Admin Directory API v1 service with admin's credentials'''
    try:
        SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']
        creds = get_creds(SCOPES, 'token_directory.json')
        service = build('admin', 'directory_v1', credentials=creds)
        return service

    except LookupError as le:
        return "Error in the key or index !!\n" + str(le)
    except ValueError as ve:
        return "Error in Value Entered !!\n" + str(ve)
    except OSError as oe:
        return "Error! " + str(oe)

def create_simulator_driveAPI_service(user_token_name):
    '''Create Drive API v3 service with user's credentials'''
    try:
        # If modifying these scopes, delete the file token.json.
        SCOPES = ['https://www.googleapis.com/auth/drive']
        user_token_name = 'tokens/' + user_token_name
        creds = get_creds(SCOPES, user_token_name)
        service = build('drive', 'v3', credentials=creds)
        return service

    except LookupError as le:
        return("Error in the key or index !!\n" + str(le))
    except ValueError as ve:
        return("Error in Value Entered !!\n" + str(ve))
    except OSError as oe:
        return("Error! " + str(oe))