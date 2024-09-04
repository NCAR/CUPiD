# CUPiD Configuration File

### This page describes the fields in the configuration file that might commonly be edited.

# <img src="../images/config_1.png" alt="CUPiD Config 1" width=1000 />
This section describes general data sources and expected directory structure for running CUPiD.
`sname`: nickname for this configuration as a string. This will be used as the name of the folder your computed notebooks are put in

# <img src="../images/config_2.png" alt="CUPiD Config 2" width=1000 />
This section supplies the default kernel for running CUPiD. This should usually be `cupid-analysis`. If a contributor wants to include additional packages, please create an issue describing the packages you'd like to add to this conda environment.

# <img src="../images/config_3.png" alt="CUPiD Config 3" width=1000 />
This section of the configuration file describes 1) global parameters that are applicable to all notebooks and 2) timeseries-related parameters specific to each component.
`CESM_output_dir`: directory where output from CESM is located.
`case_name`: name of CESM case; this should also be a subdirectory of `CESM_output_dir`.
`vars` for various components: variables which CUPiD will expect to find for various components and then make timeseries for.

# <img src="../images/config_4.png" alt="CUPiD Config 4" width=1000 />
This section of the configuration file describes the notebooks that will be computed as well as any parameters specific to those notebooks.
`adf_quick_run`: This is the name of a notebook which is added to the atmospheric component diagnostics.
`adf_path`, `config_path`, `config_fil_str`, etc: These are parameters specific to the `adf_quick_run` notebook. If a contributor wants to include additional parameters specific to a notebook, we recommend following a similar format and changing variables names to represent the relevant quantities.

# <img src="../images/config_5.png" alt="CUPiD Config 5" width=1000 />
This section describes the Juptyter Book configuration to display the output of the CUPiD diagnostics. Please include your notebook name within the files under `chapters`.
