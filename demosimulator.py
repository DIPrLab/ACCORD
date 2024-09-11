from googleapiclient.http import MediaInMemoryUpload
from serviceAPI import create_simulator_driveAPI_service
from extractSimulatorList import getFileList, getFolderList, getUserList
import random, base64, time
from datetime import datetime
from googleapiclient.errors import HttpError

# Class to initialize a user subject to perform actions
class UserSubject():
    '''Represents a user for simulating actions on Drive resources

    Attributes:
        service: googleapiclient.discovery.Resource, for interacting with Drive API
        usersList: Subset of domain users, excluding self, to choose from as targets
        userName: str, username
        userEmail: str, same as userName
    '''

    def __init__(self, user_name, user_dict):
        '''Initialize user

        Args:
            username: str
            user_dict: dictionary of target users for actions, keys will be extracted
        '''
        self.userName = user_name
        self.userEmail = self.userName
        self.service = create_simulator_driveAPI_service(user_dict[user_name])
        totalList = list(user_dict.keys())
        totalList.remove(user_name)
        self.usersList = totalList

    def fetch_file(self):
        '''Generate a dictionary of all files a user has access to'''
        # Initialize an empty dictionary to store file names and IDs
        files_dict = {}

        try:
            # Call the Drive API to list the files
            # Modify pageSize as needed; here it's set to 100 to fetch up to 100 files
            results = self.service.files().list(
                pageSize=100,
                fields="nextPageToken, files(id, name)"
            ).execute()
            
            # Get the list of files
            files = results.get('files', [])
            
            # Populate the dictionary with file names and file IDs
            for file in files:
                files_dict[file['name']] = file['id']
            
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

        return files_dict


class PerformActions():
    '''Perform actions on Drive objects for simulation purposes.

    Attributes:
        action: str, action to be performed
        userSubject: str, actor
        actionType: str
        fileID: str, object of action
        ownerName: str, object owner
        actionCount: int, actions to perform
        constraintAction:
    '''

    def __init__(self, owner, actor, action, actionType, fileID, actionIndex, constraintAction):
        self.action = action
        self.userSubject = actor
        self.actionType = actionType
        self.fileID = fileID
        self.ownerName = owner
        self.actionCount = 1
        self.actionIndex = actionIndex
        self.constraintAction = constraintAction

    def check_permissions(self, fileID):
        '''Return True if user subject has at least Editor permissions on file'''
        try:
            file = self.userSubject.service.files().get(fileId=fileID, fields="permissions").execute()
            email = self.userSubject.userEmail  # Make sure you are using the correct attribute for the user's email
            can_edit = False
            for permission in file['permissions']:
                if(email == permission.get('emailAddress') and permission.get('role') in ['writer', 'owner']):
                    can_edit = True
                    break
            return can_edit
        except HttpError as error:
            return False

    def simulate_permissionChange(self, actionType):
        '''Add, remove, or change permissions for a random user'''
        fileUserList, userIdList = getUserList(self.userSubject.service, self.fileID)
        roles = ['writer', 'commenter', 'reader'] 
        fileID = self.fileID
        if(self.check_permissions(fileID)):
            match actionType:
                # Add User to the file
                case "Add Permission":
                    new_userList = list(set(self.userSubject.usersList).difference(fileUserList))
                    newUser = random.choice(new_userList)

                    if new_userList:
                        permission = {
                            'type': 'user',
                            'role': 'writer',
                            'emailAddress': newUser
                        }
                        self.userSubject.service.permissions().create(fileId=fileID, body=permission, sendNotificationEmail=False).execute()
                        return True

                case "Remove Permission":
                    # Remove the actor ID from the user ID list and choose a random user to remove permission
                    userIdList.pop(fileUserList.index(self.userSubject.userName))
                    if userIdList:
                        # Fetch the permissions for the file
                        permissions = self.userSubject.service.permissions().list(fileId=fileID).execute()

                        # Filter the permissions to exclude the owner
                        non_owner_permissions = [
                            permission for permission in permissions.get("permissions", [])
                            if permission.get("role") != "owner" and permission.get("id") in userIdList
                        ]

                        # If there are non-owner permissions, remove a random one
                        if non_owner_permissions:
                            random_permission = random.choice(non_owner_permissions)
                            self.userSubject.service.permissions().delete(
                                fileId=fileID, permissionId=random_permission["id"]
                            ).execute()
                            return True

                case "Update Permission":
                    # Remove the actor ID from the user ID list and choose a random user to update permission
                    userIdList.pop(fileUserList.index(self.userSubject.userName))
                    if userIdList:
                        # Fetch the permissions for the file
                        permissions = self.userSubject.service.permissions().list(fileId=fileID).execute()

                        # Filter the permissions to exclude the owner
                        non_owner_permissions = [
                            permission for permission in permissions.get("permissions", [])
                            if permission.get("role") != "owner" and permission.get("id") in userIdList
                        ]

                        # If there are non-owner permissions, remove a random one
                        if non_owner_permissions:
                            userID = random.choice(non_owner_permissions)['id']
                            permission = self.userSubject.service.permissions().get(fileId=fileID, permissionId = userID).execute()
                            user_role = [permission['role']]
                            new_user_role = random.choice(list(set(roles).difference(user_role)))
                            new_permission = {'role' : new_user_role }
                            self.userSubject.service.permissions().update(fileId=fileID, permissionId = userID, body=new_permission).execute()
                            return True

                case _:
                    pass
        return False

    def simulate_edit(self):
        '''Perform edit on document by adding text'''
        fileID = self.fileID
        file = self.userSubject.service.files().get(fileId=fileID).execute()
        mime_type = file['mimeType']

        # Check if file is of Document Type
        if(mime_type == 'application/vnd.google-apps.document'):
            fileContent = "Hello World! File has been Edited on " + str(datetime.now())
            encoded_content = base64.b64encode(fileContent.encode())
            decoded_content = base64.b64decode(encoded_content).decode()
            media = MediaInMemoryUpload(decoded_content.encode(), mimetype=mime_type)
            file = self.userSubject.service.files().update(fileId=fileID, media_body=media).execute()
            return True

        return False

    def simulate_move(self, folderList):
        '''Choose a random destination from provided list and move file'''
        fileID = self.fileID
        # Retrieve the current parent(s) of the file
        file = self.userSubject.service.files().get(fileId=fileID, fields='parents').execute()
        if file:
            previous_parents = ",".join(file['parents'])
            old_parents_list = file['parents']
            total_FolderList = folderList
            new_FolderList = list(set(total_FolderList).difference(old_parents_list))
            if new_FolderList and fileID not in new_FolderList:
                # Move the file to the new folder
                newFolder = random.choice(new_FolderList)
                self.userSubject.service.files().update(fileId=fileID, addParents=newFolder, removeParents=previous_parents, fields='id, parents').execute()
                return True

        return True

    def simulate_delete(self):
        '''Delete file if user has at least "Editor" permissions'''
        fileID = self.fileID
        if(self.check_permissions(fileID)):
            self.userSubject.service.files().delete(fileId=fileID).execute()
            return True

        return False
    
    def simulate_create(self, inFolder):
        '''Choose a parent at random and create file

        Args:
            inFolder: boolean, whether to put file in folder instead of 'Root'
        '''
        # Define the file metadata
        total_FolderList = getFolderList(self.userSubject.service)
        fruitNames = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape", "honeydew", "kiwi", "lemon", "orange", "peach", "pear", "pineapple", "strawberry", "watermelon", "london", "paris", "newyork", "tokyo", "berlin", "mumbai", "report", "document", "presentation", "spreadsheet", "invoice", "receipt"]
        file_metadata = {
            'name': random.choice(fruitNames) + '_' + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.docx',
            'mimeType': 'application/vnd.google-apps.document'
            }
        if(inFolder):
            file_metadata['parents'] = [random.choice(total_FolderList)]
        
        fileID = self.userSubject.service.files().create(body=file_metadata, media_body=None).execute()
        self.fileID = fileID.get('id')
        return True
    
    def perform_actions(self, actorsDict):
        '''Execute action specified at initialization'''
        try:
            # Perform actions until the action Count parameters is zero
            while(self.actionCount > 0):
                simval = False
                # Choose an actor and an action
                action = self.action              

                fileList = getFileList(self.userSubject.service)
                folderList = getFolderList(self.userSubject.service)

                # Simulate Actions based on action selected
                match action:
                    case "Create":
                        simval = self.simulate_create(False)

                    case "Delete":
                        #file_object = self.fileobject
                        simval =self.simulate_delete()
                        if(simval):
                            self.fileID = 'None'

                    case "Edit":
                        simval = self.simulate_edit()

                    case "Move":
                        #file_object = self.fileobject
                        simval = self.simulate_move(folderList)

                    case "Permission Change":
                        #file_object = self.fileobject
                        if(self.actionIndex <3):
                            actionType = "Add Permission"                                 
                        elif(self.actionIndex == 3 and self.action == "Permission Change"):
                            actionType = self.actionType
                        else:
                            actionTypes = ['Add Permission', 'Remove Permission', 'Update Permission']
                            actionType = random.choice(actionTypes)
                        simval = self.simulate_permissionChange(actionType)

                    case _:
                        pass

                if(simval):
                    self.actionCount -= 1
                    time.sleep(2)

            return self.fileID

        except LookupError as le:
            return("Error in the key or index !!\n" + str(le))
        except ValueError as ve:
            return("Error in Value Entered !!\n" + str(ve))
        except TypeError as te:
            return("Error in Type matching !!\n" + str(te))  