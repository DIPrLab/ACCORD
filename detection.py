from extractDriveFiles import getFileList, getDomainUserList

def get_filteroptions(driveAPI_service, directoryAPI_service):
    '''Generate lists of options for UI comboboxes using services

    Returns: two lists, one of filenames and one of domain users'''
    # Set up Fields of Documents ComboBox
    fileList = ["Any"]
    files, fids = getFileList(driveAPI_service)
    if(len(files) > 0):
        fileList.extend(files)

    # Set up fields for Actors ComboBox
    actorList = ["Any"]
    users = getDomainUserList(directoryAPI_service)
    if(len(users) > 0):
        actorList.extend(users)

    return actorList, fileList