#!/bin/bash -e
# This script is run by the CESM workflow when RUN_POSTPROCESSING=TRUE,
# it is invoked from case.cupid and the expectation is that it is run
# from CASEROOT.
# One possible future development would be to make case.cupid a python script
# and then update this to python as well (and take a CIME Case object as
# an argument)


# Set variables that come from environment or CESM XML files
CASEROOT=${PWD}
SRCROOT=`./xmlquery --value SRCROOT`
CESM_CUPID=${SRCROOT}/tools/CUPiD
CUPID_ROOT=`./xmlquery --value CUPID_ROOT`
CUPID_EXAMPLE=`./xmlquery --value CUPID_EXAMPLE`
CUPID_GEN_TIMESERIES=`./xmlquery --value CUPID_GEN_TIMESERIES`
CUPID_GEN_DIAGNOSTICS=`./xmlquery --value CUPID_GEN_DIAGNOSTICS`
CUPID_GEN_HTML=`./xmlquery --value CUPID_GEN_HTML`
CUPID_BASELINE_CASE=`./xmlquery --value CUPID_BASELINE_CASE`
CUPID_BASELINE_ROOT=`./xmlquery --value CUPID_BASELINE_ROOT`
CUPID_TS_DIR=`./xmlquery --value CUPID_TS_DIR`
CUPID_STARTDATE=`./xmlquery --value CUPID_STARTDATE`
CUPID_STOP_N=`./xmlquery --value CUPID_STOP_N`
CUPID_STOP_OPTION=`./xmlquery --value CUPID_STOP_OPTION`
CALENDAR=`./xmlquery --value CALENDAR`
CUPID_BASE_STARTDATE=`./xmlquery --value CUPID_BASE_STARTDATE`
CUPID_BASE_STOP_N=`./xmlquery --value CUPID_BASE_STOP_N`
CUPID_BASE_STOP_OPTION=`./xmlquery --value CUPID_BASE_STOP_OPTION`
CUPID_CLIMO_START_YEAR=`./xmlquery --value CUPID_CLIMO_START_YEAR`
CUPID_BASE_CLIMO_START_YEAR=`./xmlquery --value CUPID_BASE_CLIMO_START_YEAR`
CUPID_CLIMO_N_YEAR=`./xmlquery --value CUPID_CLIMO_N_YEAR`
CUPID_BASE_CLIMO_N_YEAR=`./xmlquery --value CUPID_BASE_CLIMO_N_YEAR`
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
# cupid-analysis env required for end date calculation
conda activate ${CUPID_ANALYSIS_ENV}

# Calculate CUPID_ENDDATE and CUPID_BASE_ENDDATE
# calendar name needs to be changed for cftime standards
CFTIME_CALENDAR=$CALENDAR
CFTIME_CALENDAR="${CFTIME_CALENDAR/GREGORIAN/proleptic_gregorian}"
CFTIME_CALENDAR="${CFTIME_CALENDAR/NO_LEAP/noleap}"
CUPID_ENDDATE=`${CUPID_ROOT}/helper_scripts/find_enddate.py \
  --start-date ${CUPID_STARTDATE} \
  --stop-option ${CUPID_STOP_OPTION} \
  --stop-n ${CUPID_STOP_N} \
  --calendar ${CFTIME_CALENDAR}`
CUPID_BASE_ENDDATE=`${CUPID_ROOT}/helper_scripts/find_enddate.py \
  --start-date ${CUPID_BASE_STARTDATE} \
  --stop-option ${CUPID_BASE_STOP_OPTION} \
  --stop-n ${CUPID_BASE_STOP_N} \
  --calendar ${CFTIME_CALENDAR}`

# Note if CUPID_ROOT is not tools/CUPiD
# (but don't complain if user adds a trailing "/")
if [ "${CUPID_ROOT%/}" != "${CESM_CUPID}" ]; then
  echo "Note: Running CUPiD from ${CUPID_ROOT}, not ${CESM_CUPID}"
fi

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
${CUPID_ROOT}/helper_scripts/generate_cupid_config_for_cesm_case.py \
   ${CVDP_OPT} \
   --case-root ${CASEROOT} \
   --cesm-root ${SRCROOT} \
   --cupid-root ${CUPID_ROOT} \
   --cupid-example ${CUPID_EXAMPLE} \
   --cupid-baseline-case ${CUPID_BASELINE_CASE} \
   --cupid-baseline-root ${CUPID_BASELINE_ROOT} \
   --cupid-ts-dir ${CUPID_TS_DIR} \
   --cupid-startdate ${CUPID_STARTDATE} \
   --cupid-enddate ${CUPID_ENDDATE} \
   --cupid-base-startdate ${CUPID_BASE_STARTDATE} \
   --cupid-base-enddate ${CUPID_BASE_ENDDATE} \
   --cupid-climo-start-year ${CUPID_CLIMO_START_YEAR} \
   --cupid-climo-n-year ${CUPID_CLIMO_N_YEAR} \
   --cupid-base-climo-start-year ${CUPID_BASE_CLIMO_START_YEAR} \
   --cupid-base-climo-n-year ${CUPID_BASE_CLIMO_N_YEAR} \
   --adf-output-root ${PWD} \
   --ldf-output-root ${PWD} \
   --ilamb-output-root ${PWD} \
   --cupid-run-adf ${CUPID_RUN_ADF} \
   --cupid-run-ldf ${CUPID_RUN_LDF} \
   --cupid-run-ilamb ${CUPID_RUN_ILAMB}

# 2. Generate ADF config file
if [ "${CUPID_RUN_ADF}" == "TRUE" ]; then
  ${CUPID_ROOT}/helper_scripts/generate_adf_config_file.py \
     --cupid-config-loc . \
     --adf-template ${CUPID_ROOT}/externals/ADF/config_amwg_default_plots.yaml \
     --out-file adf_config.yml
fi

# 3. Generate ILAMB config file
if [ "${CUPID_RUN_ILAMB}" == "TRUE" ]; then
  ${SRCROOT}/tools/CUPiD/helper_scripts/generate_ilamb_config_files.py \
     --cupid-config-loc . \
     --run-type ${CUPID_RUN_TYPE} \
     --cupid-root ${CUPID_ROOT}
fi

# 4. Generate LDF config file
if [ "${CUPID_RUN_LDF}" == "TRUE" ]; then
  ${CUPID_ROOT}/helper_scripts/generate_ldf_config_file.py \
     --cupid-config-loc . \
     --ldf-template ${CUPID_ROOT}/externals/LDF/config_clm_unstructured_plots.yaml \
     --out-file ldf_config.yml
fi

# 5. Generate timeseries files
if [ "${CUPID_GEN_TIMESERIES}" == "TRUE" ]; then
   ${CUPID_ROOT}/cupid/run_timeseries.py ${CUPID_FLAG_STRING}
fi

# 6. Run ADF
if [ "${CUPID_RUN_ADF}" == "TRUE" ]; then
  conda deactivate
  conda activate ${CUPID_ANALYSIS_ENV}
  ${CUPID_ROOT}/externals/ADF/run_adf_diag adf_config.yml
fi

# 7. Run ILAMB
if [ "${CUPID_RUN_ILAMB}" == "TRUE" ]; then
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
