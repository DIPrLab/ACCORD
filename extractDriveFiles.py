def getFileList(service):
    '''Using Drive API service, returns list of filenames and list of ids'''
    result = service.files().list(fields="files(id, name)").execute()

    # Extract the list from the dictionary
    file_list = result.get('files')
    FList = []
    FidList = []
    for item in file_list:
        FidList.append(item['id'])
        FList.append(item['name'])

    return FList,FidList

def getFolderList(service):
    '''Using Drive API service, returns list of folder names'''
    resource = service.files()
    result = resource.list(fields="files(id, name)", q="mimeType='application/vnd.google-apps.folder'").execute()

    # Extract the list from the dictionary
    folder_list = result.get('files')
    FList = []
    for item in folder_list:
        FList.append(item['id'])

    return FList

def getUserList(service, file_id):
    '''Using Drive API, returns users with permissions on file'''
    file = service.files().get(fileId=file_id, fields='*').execute()
    userList = []
    userId = []
    for item in file['permissions']:
        userList.append(item['emailAddress'])
        userId.append(item['id'])

    return userList, userId

def getDomainUserList(service):
    '''List all emails for domain users'''
    results = service.users().list(customer='my_customer', orderBy='email').execute()
    users = results.get('users', [])
    userList = []
    for user in users:
        userList.append(user['primaryEmail'])
    
    return userList

def getUserID(service, fileID, email):
    '''Get the user ID for a user with permissions on a file'''
    permissions = service.permissions().list(fileId=fileID, fields="*").execute()
    for permission in permissions.get('permissions', []):
        if(permission['emailAddress'] == email):
            return permission['id']