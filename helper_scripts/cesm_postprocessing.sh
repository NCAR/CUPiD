#!/bin/bash -e
# This script is run by the CESM workflow when RUN_POSTPROCESSING=TRUE,
# it is invoked from case.cupid and the expectation is that it is run
# from CASEROOT.
# One possible future development would be to make case.cupid a python script
# and then update this to python as well (and take a CIME Case object as
# an argument)

# Function to add some number of years to a string that
# is formatted as YYYY-MM-DD and print out the updated
# string in the same format
add_years() {
  IFS='-' read -r YEAR MM DD <<< "$1"
  YEAR=$((10#$YEAR))  # Force base-10
  MM=$((10#$MM))
  DD=$((10#$DD))
  NEW_YEAR=`printf '%04d' "$((YEAR + $2))"`-`printf '%02d' "${MM}"`-`printf '%02d' "${DD}"`
  echo ${NEW_YEAR}
}

# Set variables that come from environment or CESM XML files
CASEROOT=${PWD}
SRCROOT=`./xmlquery --value SRCROOT`
CUPID_EXAMPLE=`./xmlquery --value CUPID_EXAMPLE`
CUPID_GEN_TIMESERIES=`./xmlquery --value CUPID_GEN_TIMESERIES`
CUPID_GEN_DIAGNOSTICS=`./xmlquery --value CUPID_GEN_DIAGNOSTICS`
CUPID_GEN_HTML=`./xmlquery --value CUPID_GEN_HTML`
CUPID_BASELINE_CASE=`./xmlquery --value CUPID_BASELINE_CASE`
CUPID_BASELINE_ROOT=`./xmlquery --value CUPID_BASELINE_ROOT`
CUPID_TS_DIR=`./xmlquery --value CUPID_TS_DIR`
CUPID_STARTDATE=`./xmlquery --value CUPID_STARTDATE`
CUPID_NYEARS=`./xmlquery --value CUPID_NYEARS`
CUPID_ENDDATE=`add_years ${CUPID_STARTDATE} ${CUPID_NYEARS}`
CUPID_BASE_STARTDATE=`./xmlquery --value CUPID_BASE_STARTDATE`
CUPID_BASE_NYEARS=`./xmlquery --value CUPID_BASE_NYEARS`
CUPID_BASE_ENDDATE=`add_years ${CUPID_BASE_STARTDATE} ${CUPID_BASE_NYEARS}`
CUPID_RUN_SERIAL=`./xmlquery --value CUPID_RUN_SERIAL`
CUPID_RUN_ALL=`./xmlquery --value CUPID_RUN_ALL`
CUPID_RUN_ATM=`./xmlquery --value CUPID_RUN_ATM`
CUPID_RUN_OCN=`./xmlquery --value CUPID_RUN_OCN`
CUPID_RUN_LND=`./xmlquery --value CUPID_RUN_LND`
CUPID_RUN_ICE=`./xmlquery --value CUPID_RUN_ICE`
CUPID_RUN_ROF=`./xmlquery --value CUPID_RUN_ROF`
CUPID_RUN_GLC=`./xmlquery --value CUPID_RUN_GLC`
CUPID_RUN_ADF=`./xmlquery --value CUPID_RUN_ADF`
CUPID_INFRASTRUCTURE_ENV=`./xmlquery --value CUPID_INFRASTRUCTURE_ENV`
CUPID_ANALYSIS_ENV=`./xmlquery --value CUPID_ANALYSIS_ENV`

# Create directory for running CUPiD
mkdir -p cupid-postprocessing
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

if [ "${CUPID_RUN_SERIAL}" == "TRUE" ]; then
  echo "CUPiD will not use dask in any notebooks"
  CUPID_FLAG_STRING+=" --serial"
fi

if [ "${CUPID_RUN_ALL}" == "TRUE" ]; then
  echo "CUPID_RUN_ALL is True, running diagnostics for all components"
fi

# Use cupid-infrastructure environment for running these scripts
# Note: on derecho, the cesmdev module creates a python conflict
#       by setting $PYTHONPATH; since this is conda-based we
#       want an empty PYTHONPATH environment variable
unset PYTHONPATH
conda activate ${CUPID_INFRASTRUCTURE_ENV}

# 1. Generate CUPiD config file
${SRCROOT}/tools/CUPiD/helper_scripts/generate_cupid_config_for_cesm_case.py \
   --cesm-root ${SRCROOT} \
   --case-root ${CASEROOT} \
   --adf-output-root ${PWD} \
   --cupid-example ${CUPID_EXAMPLE} \
   --cupid-baseline-case ${CUPID_BASELINE_CASE} \
   --cupid-baseline-root ${CUPID_BASELINE_ROOT} \
   --cupid-ts-dir ${CUPID_TS_DIR} \
   --cupid-startdate ${CUPID_STARTDATE} \
   --cupid-enddate ${CUPID_ENDDATE} \
   --cupid-base-startdate ${CUPID_BASE_STARTDATE} \
   --cupid-base-enddate ${CUPID_BASE_ENDDATE} \

# 2. Generate ADF config file
if [ "${CUPID_RUN_ADF}" == "TRUE" ]; then
  ${SRCROOT}/tools/CUPiD/helper_scripts/generate_adf_config_file.py \
     --cesm-root ${SRCROOT} \
     --cupid-config-loc . \
     --adf-template ${SRCROOT}/tools/CUPiD/externals/ADF/config_amwg_default_plots.yaml \
     --out-file adf_config.yml
fi

# 3. Generate timeseries files
if [ "${CUPID_GEN_TIMESERIES}" == "TRUE" ]; then
   ${SRCROOT}/tools/CUPiD/cupid/run_timeseries.py ${CUPID_FLAG_STRING}
fi

#4. Run ADF
if [ "${CUPID_RUN_ADF}" == "TRUE" ]; then
  conda deactivate
  conda activate ${CUPID_ANALYSIS_ENV}
  ${SRCROOT}/tools/CUPiD/externals/ADF/run_adf_diag adf_config.yml
fi

# 5. Run CUPiD and build webpage
conda deactivate
conda activate ${CUPID_INFRASTRUCTURE_ENV}
if [ "${CUPID_GEN_DIAGNOSTICS}" == "TRUE" ]; then
  ${SRCROOT}/tools/CUPiD/cupid/run_diagnostics.py ${CUPID_FLAG_STRING}
fi
if [ "${CUPID_GEN_HTML}" == "TRUE" ]; then
  ${SRCROOT}/tools/CUPiD/cupid/cupid_webpage.py
fi
