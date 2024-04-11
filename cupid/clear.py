#!/usr/bin/env python
import os
import sys
import click
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
        print(f"Error occurred while clearing contents in {folderPath}: {e}")

def readConfigFile(config_path):
    #Given the file path to config.yml, this function reads the config file content and 
    #returns the val of the run_dir string with '/computed_notebooks' appended to it 
    
    #Obtain the contents of the config.yml file and extract the run_dir variable
    control = cupid.util.get_control_dict(config_path)
    run_dir = control['data_sources'].get('run_dir', None)
    
    if run_dir:
        #Append '/computed_notebooks' to the run_dir value if it is not empty
        fullPath = os.path.join(run_dir, 'computed_notebooks')
        return fullPath
    
    else: #run_dir is empty/wasn't found in config file so return error
        print("ERROR: 'run_dir' was empty/not found in the config file.")
        sys.exit(1)

@click.command()
@click.argument('config_path')
#Entry point to this script
def clear(config_path):
    run_dir = readConfigFile(config_path)
    clearFolder(run_dir)