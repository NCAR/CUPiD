#!/usr/bin/env python3
import argparse
import yaml
import os

def _parse_args():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        description="Generate cupid_adf_config.yml based on an existing CUPID YAML file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--cupid_file",
                        action="store",
                        required=True,
                        help="CUPID YAML file")
    parser.add_argument("--adf_template",
                        action='store',
                        required=True,
                        help="an adf config file to use as a base")
    parser.add_argument("--out_file", action='store', required=True, help='the output file to save')
    return parser.parse_args()


def generate_adf_config(cupid_file, adf_file, out_file):
    """Use cupid_file (YAML) and adf_file (YAML) to produce out_file
       by modifying adf_file with data from cupid_file.
    """
    with open(cupid_file, encoding='UTF-8') as c:
        c_dict = yaml.load(c, Loader=yaml.SafeLoader)
    with open(adf_file, encoding='UTF-8') as a:
        a_dict = yaml.load(a, Loader=yaml.SafeLoader)

    # Mapping from CUPID's global_params:
    a_dict['diag_cam_climo']['cam_case_name'] = c_dict['global_params']['case_name']
    a_dict['diag_cam_baseline_climo']['cam_case_name'] = c_dict['global_params']['base_case_name']

    # QUESTION: how to specify locations for model output?
    # - separate history files, time series files, climo files ? 
    # - separate for 'base case' and 'test case(s)'?
    a_dict['diag_cam_climo']['cam_hist_loc'] = c_dict['global_params']['CESM_output_dir']
    a_dict['diag_cam_baseline_climo']['cam_hist_loc'] = c_dict['global_params']['CESM_output_dir']

    # QUESTION: how to specify different start/end dates for 'base case' and 'test case(s)'?
    a_dict['diag_cam_climo']['start_year'] = int(c_dict['global_params']['start_date'].split('-')[0])
    a_dict['diag_cam_climo']['end_year'] = int(c_dict['global_params']['end_date'].split('-')[0])
    a_dict['diag_cam_baseline_climo']['start_year'] = int(c_dict['global_params']['start_date'].split('-')[0])
    a_dict['diag_cam_baseline_climo']['end_year'] = int(c_dict['global_params']['end_date'].split('-')[0])

    a_dict['diag_basic_info']['num_procs'] = c_dict['timeseries'].get('num_procs', 1)

    a_dict['user'] = os.getenv("USER")

    with open(out_file, "w") as f:
        # Header of file is a comment logging provenance
        f.write(f"# This file has been auto-generated using generate_adf_config_file.py\n")
        f.write("# Arguments:\n")
        f.write(f"# {cupid_file = }\n")
        f.write(f"# {adf_file = }\n")
        f.write(f"# Output: {out_file = }\n")
        # enter in each element of the dictionary into the new file
        yaml.dump(a_dict, f, sort_keys=False)


if __name__ == "__main__":
    args = vars(_parse_args())
    print(args)
    generate_adf_config(args['cupid_file'], args['adf_template'], args['out_file'])