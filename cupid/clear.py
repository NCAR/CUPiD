#!/usr/bin/env python
import os
import cupid.util

def clearFolder(folderPath):
    #Clears all contents in the specified folder at folderPath (i.e. computed_notebooks)
    try:
        # Iterate over all items in the folder
        for item in os.listdir(folderPath):
            itemPath = os.path.join(folderPath, item)
            # If item is a file, delete it
            if os.path.isfile(itemPath):
                os.remove(itemPath)  
            # If item is a directory, recursively clear it
            elif os.path.isdir(itemPath):
                clearFolder(itemPath)   
        # After deleting all items, remove the folder itself
        os.rmdir(folderPath)    
        print(f"All contents in {folderPath} have been cleared.")
    except Exception as e:
        print(f"Error occurred while clearing contents of the file at path {folderPath}: {e}")

def readConfigFile(configFilePath):
    #Given the file path to config.yml, this function reads the config file content and 
    #returns the val of the run_dir string with '/computed_notebooks' appended to it 
    try:
        #Obtain the contents of the config.yml file and extract the run_dir variable
        control = cupid.util.get_control_dict(configFilePath)
        run_dir = control['data_sources']['run_dir']
        
        if run_dir:
            #Append '/computed_notebooks' to the run_dir value if it is not empty
            fullPath = os.path.join(run_dir, 'computed_notebooks')
            return fullPath
        else: #run_dir is empty/wasn't found in config file so return error
            raise ValueError("'run_dir' was not found in the config file.")
    except FileNotFoundError:
        print(f"config.yml at path'{configFilePath}' not found.")
    except Exception as e:
        print(f"Error occurred while reading config file at path '{configFilePath}': {e}")
    return None

#Entry point to this script
def clear():
    #Get the current working directory and add 'config.yml' to the path to 
    #obtain the path to the config.yml file in the current working directory
    currWorkingDir =  os.getcwd() 
    configFilePath = os.path.join(currWorkingDir, 'config.yml')

    run_dir = readConfigFile(configFilePath)

    if run_dir:
        clearFolder(run_dir)