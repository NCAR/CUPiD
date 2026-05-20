#!/bin/bash -e
# This script is run by the CESM workflow when RUN_POSTPROCESSING=TRUE,
# it is invoked from case.cupid and the expectation is that it is run
# from CASEROOT.
# One possible future development would be to make case.cupid a python script
# and then update this to python as well (and take a CIME Case object as
# an argument)


# Set variables that come from environment or CESM XML files
SRCROOT=`./xmlquery --value SRCROOT`
CUPID_ROOT=`./xmlquery --value CUPID_ROOT`
CUPID_GEN_TIMESERIES=`./xmlquery --value CUPID_GEN_TIMESERIES`
CUPID_GEN_DIAGNOSTICS=`./xmlquery --value CUPID_GEN_DIAGNOSTICS`
CUPID_GEN_HTML=`./xmlquery --value CUPID_GEN_HTML`
CUPID_NTASKS=`./xmlquery --value CUPID_NTASKS`
CUPID_RUN_ALL=`./xmlquery --value CUPID_RUN_ALL`
CUPID_RUN_ATM=`./xmlquery --value CUPID_RUN_ATM`
CUPID_RUN_OCN=`./xmlquery --value CUPID_RUN_OCN`
CUPID_RUN_LND=`./xmlquery --value CUPID_RUN_LND`
CUPID_RUN_ICE=`./xmlquery --value CUPID_RUN_ICE`
CUPID_RUN_ROF=`./xmlquery --value CUPID_RUN_ROF`
CUPID_RUN_GLC=`./xmlquery --value CUPID_RUN_GLC`
CUPID_RUN_ADF=`./xmlquery --value CUPID_RUN_ADF`
CUPID_RUN_CVDP=`./xmlquery --value CUPID_RUN_CVDP`
CUPID_RUN_LDF=`./xmlquery --value CUPID_RUN_LDF`
CUPID_RUN_ILAMB=`./xmlquery --value CUPID_RUN_ILAMB`
CUPID_RUN_TYPE=`./xmlquery --value CUPID_RUN_TYPE`
CUPID_INFRASTRUCTURE_ENV=`./xmlquery --value CUPID_INFRASTRUCTURE_ENV`
CUPID_ANALYSIS_ENV=`./xmlquery --value CUPID_ANALYSIS_ENV`

# Note: on derecho, the cesmdev module creates a python conflict
#       by setting $PYTHONPATH; since this is conda-based we
#       want an empty PYTHONPATH environment variable
unset PYTHONPATH

# Change to directory for running cupid postprocessing
cd cupid-postprocessing

# If CUPID_RUN_ALL is TRUE, we don't add any component flags.
# The lack of any component flags tells CUPiD to run all components.
CUPID_FLAG_STRING=""
if [ "${CUPID_RUN_ALL}" == "FALSE" ]; then
  if [ "${CUPID_RUN_ATM}" == "TRUE" ]; then
    CUPID_FLAG_STRING+=" -atm"
  fi
  if [ "${CUPID_RUN_OCN}" == "TRUE" ]; then
    CUPID_FLAG_STRING+=" -ocn"
  fi
  if [ "${CUPID_RUN_LND}" == "TRUE" ]; then
    CUPID_FLAG_STRING+=" -lnd"
  fi
  if [ "${CUPID_RUN_ICE}" == "TRUE" ]; then
    CUPID_FLAG_STRING+=" -ice"
  fi
  if [ "${CUPID_RUN_ROF}" == "TRUE" ]; then
    CUPID_FLAG_STRING+=" -rof"
  fi
  if [ "${CUPID_RUN_GLC}" == "TRUE" ]; then
    CUPID_FLAG_STRING+=" -glc"
  fi
  if [ "${CUPID_FLAG_STRING}" == "" ]; then
    echo "If CUPID_RUN_ALL is False, user must set at least one component"
    exit 1
  fi
fi

if [ "${CUPID_NTASKS}" == "1" ]; then
  echo "CUPiD will not use dask in any notebooks"
  CUPID_FLAG_STRING+=" --serial"
fi

if [ "${CUPID_RUN_ALL}" == "TRUE" ]; then
  echo "CUPID_RUN_ALL is True, running diagnostics for all components"
fi

# Use cupid-infrastructure environment for running these scripts
conda activate ${CUPID_INFRASTRUCTURE_ENV}

# 1. Generate CUPiD config file
if [ "${CUPID_RUN_CVDP}" == "TRUE" ]; then
  if [ "${CUPID_RUN_ADF}" != "TRUE" ]; then
    echo "ERROR: CUPID_RUN_CVDP=TRUE but CUPID_RUN_ADF=${CUPID_RUN_ADF}. CVDP is run by"
    echo "the ADF, so that combination of flags will result in CVDP not being run."
    echo "Either set CUPID_RUN_ADF=TRUE or CUPID_RUN_CVDP=FALSE"
    exit 1
  fi
  CVDP_OPT="--run-cvdp"
else
  CVDP_OPT=""
fi

#
# Steps to setup the configure files has already been done in preview_namelists
#
#
# Run the CUPiD Processing
#

# 5. Generate timeseries files
if [ "${CUPID_GEN_TIMESERIES}" == "TRUE" ]; then
   ${CUPID_ROOT}/cupid/run_timeseries.py ${CUPID_FLAG_STRING}
fi

# 6. Run ADF
if [ "${CUPID_RUN_ADF}" == "TRUE" ]; then
  if [[ "${CUPID_RUN_ALL}" == "FALSE" ]] && [[ "${CUPID_RUN_ATM}" == "FALSE" ]]; then
    echo "WARNING: Running ADF but Atmosphere component is turned off. Turn on either CUPID_RUN_ATM or CUPID_RUN_ALL to view ADF output in final webpage"
  fi
  conda deactivate
  conda activate ${CUPID_ANALYSIS_ENV}
  ${CUPID_ROOT}/externals/ADF/run_adf_diag adf_config.yml
fi

# 7. Run ILAMB
if [ "${CUPID_RUN_ILAMB}" == "TRUE" ]; then
  if [[ "${CUPID_RUN_ALL}" == "FALSE" ]] && [[ "${CUPID_RUN_LND}" == "FALSE" ]]; then
    echo "WARNING: Running ILAMB but Land component is turned off. Turn on either CUPID_RUN_LND or CUPID_RUN_ALL to view ILAMB output in final webpage"
  fi
  echo "WARNING: you may need to increase wallclock time (eg, ./xmlchange --subgroup case.cupid JOB_WALLCLOCK_TIME=06:00:00) before running ILAMB"
  conda deactivate
  conda activate ${CUPID_ANALYSIS_ENV}
  export ILAMB_ROOT=ilamb_aux
  if [ -d "ILAMB_output" ]; then
    echo "WARNING: ILAMB_output directory already exists. You may need to clear it before running ILAMB."
  fi
  ilamb-run --config ilamb_nohoff_final_CLM_${CUPID_RUN_TYPE}.cfg --build_dir ILAMB_output/ --df_errs ${ILAMB_ROOT}/quantiles_Whittaker_cmip5v6.parquet --define_regions ${ILAMB_ROOT}/DATA/regions/LandRegions.nc ${ILAMB_ROOT}/DATA/regions/Whittaker.nc --regions global --model_setup model_setup.txt --filter .clm2.h0.
fi

# 8. Run LDF
if [ "${CUPID_RUN_LDF}" == "TRUE" ]; then
  if [[ "${CUPID_RUN_ALL}" == "FALSE" ]] && [[ "${CUPID_RUN_LND}" == "FALSE" ]]; then
    echo "WARNING: Running LDF but Land component is turned off. Turn on either CUPID_RUN_LND or CUPID_RUN_ALL to view ILAMB output in final webpage"
  fi
  conda deactivate
  conda activate ${CUPID_ANALYSIS_ENV}
  ${CUPID_ROOT}/externals/LDF/run_adf_diag ldf_config.yml
fi

# 9. Run CUPiD and build webpage
conda deactivate
conda activate ${CUPID_INFRASTRUCTURE_ENV}
if [ "${CUPID_GEN_DIAGNOSTICS}" == "TRUE" ]; then
  ${CUPID_ROOT}/cupid/run_diagnostics.py ${CUPID_FLAG_STRING}
fi
if [ "${CUPID_GEN_HTML}" == "TRUE" ]; then
  ${CUPID_ROOT}/cupid/generate_webpage.py
fi
