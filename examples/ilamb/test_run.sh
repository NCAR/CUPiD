#!/bin/bash -e

#conda activate cupid-analysis
export ILAMB_ROOT=../../ilamb_aux
mpiexec ilamb-run --config ilamb_nohoff_final_CLM.cfg --build_dir bld/ --df_errs ../../ilamb_aux/quantiles_Whittaker_cmip5v6.parquet --define_regions ../../ilamb_aux/DATA/regions/LandRegions.nc ../../ilamb_aux/DATA/regions/Whittaker.nc --regions global --model_setup model_setup.txt --filter .clm2.h0.
