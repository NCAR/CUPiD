#!/usr/bin/env python3

#import packages
import yaml
from standard_script_setup import *
import os
from CIME.case import Case

#Create variable for the caseroot environment variable
caseroot = os.getcwd()
#Open the config.yml file and create a dictionary with safe_load from the yaml package
with open('config_template.yml') as f: 
    my_dict = yaml.safe_load(f)

# get environment cesm case variables
with Case(caseroot, read_only=False, record=True) as case:
    cime_case = case.get_value('CASE')
    #create variable to access cesm_output_dir
    outdir = case.get_value('DOUT_S_ROOT')

my_dict['global_params']['case_name'] = cime_case
my_dict['timeseries']['case_name'] = cime_case

#create variable user to access the user environment variable
user = os.environ['USER']
#replace USER with the environment variable
#my_dict['data_sources']['nb_path_root'] = f'/glade/u/home/{user}/CUPiD/examples/nblibrary'

#replace with environment variable
my_dict['global_params']['CESM_output_dir'] = outdir

#create new file, make it writeable 
with open('config.yml', "w") as f:
    #write a comment
    f.write("# sample comment\n")
    #enter in each element of the dictionary into the new file
    yaml.dump(my_dict, f)