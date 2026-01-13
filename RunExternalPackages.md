# Running External Diagnostic Packages through CUPiD

See [installation](https://ncar.github.io/CUPiD/index.html) and [setup information](https://ncar.github.io/CUPiD/run_sandalone.html) before going through these instructions.

This page describes running external diagnostic packages via CUPiD when running Standalone CUPiD. Through the CESM workflow, this is automated.

## Generate configuration files for external diagnostic packages based on CUPiD configuration file using helper scripts.
Some example commands that would be run from the `examples/key_metrics` directory may look like this:
`conda activate cupid-analysis`

Generate ADF config file:
`../../helper_scripts/generate_adf_config_file.py --cupid-config-loc .  --adf-template ../../externals/ADF/config_amwg_default_plots.yaml --out-file adf_config.yml`

Generate LDF config file:
`../../helper_scripts/generate_ldf_config_file.py --cupid-config-loc . --ldf-template ../../externals/LDF/config_clm_unstructured_plots.yaml --out-file ldf_config.yml`

Generate ILAMB config files:
`../../helper_scripts/generate_ilamb_config_files.py --cupid-config-loc . --run-type BGC --cupid-root ../../`

Note: Anything you change in the CUPiD configuration file will overwrite default external diagnostic package configuration file values (eg, from LDF). If values are not specified in the CUPiD config.yml, they will by default be set to the default external diagnostic package config file values.

## Running External Diagnostics
1) request resources-- eg, at NCAR, this may be useful: `qinteractive -l select=1:ncpus=12:mem=120GB -l walltime=08:00:00`
2) `conda activate cupid-analysis`
3) `module load nco
`
### Run LDF
`../../externals/LDF/run_adf_diag ldf_config.yml`
[More information on LDF](https://github.com/NCAR/ADF/tree/clm-diags)

### Run ADF
`../../externals/ADF/run_adf_diag adf_config.yml`
[More information on ADF](https://github.com/NCAR/ADF)

Note: you can run CVDP by turning on `run_cvdp` in the ADF section of the config file, and then running ADF as described above.
[More information on CVDP](https://github.com/NCAR/CVDP)

### Run ILAMB
Follow instructions that were printed when you generated the ILAMB config file, eg something like this:
`conda activate cupid-analysis`
`export ILAMB_ROOT=../../ilamb_aux`
`ilamb-run --config ilamb_nohoff_final_CLM_BGC.cfg --build_dir ILAMB_output/ --df_errs ${ILAMB_ROOT}/quantiles_Whittaker_cmip5v6.parquet --define_regions ${ILAMB_ROOT}/DATA/regions/LandRegions.nc ${ILAMB_ROOT}/DATA/regions/Whittaker.nc --regions global --model_setup model_setup.txt --filter .clm2.h0`
Note: If the `ILAMB_output` directory already exists in the example, remove it before re-running ILAMB.
[More information on ILAMB](https://github.com/rubisco-sfa/ILAMB)


## Note: it is best to wait to run the CUPiD Diagnostic notebooks until the webpages have been created for the external diagnostics above. Eg, these files should exist if you want external diagnostic output to be linked properly to the final cupid webpages:
* `ADF_output/*/website/index.html`
* `LDF_output/*/website/index.html`
* `CVDP_output/*/output/index.html`
* `ILAMB_output/ ... *nc`

## View output
The easiest way to view output from ALL of these packages is to continue with the [steps to run cupid diagnostic notebooks and generate a jupyter book containing output](https://ncar.github.io/CUPiD/run_standalone.html).
