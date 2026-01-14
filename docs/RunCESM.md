# Running CUPiD via CESM Workflow

CUPiD can be run either independently or via the CESM workflow. If you want to install CUPiD and run directly, we recommend looking at the [Run Standalone](https://ncar.github.io/CUPiD/run_standalone.html) pages. If you already have CESM installed and want to run CUPiD after the short term archiver is run as part of the CESM workflow, you have come to the right place!

## Setup
Install cupid analysis and infrastructure environments per the [usual setup instructions](https://ncar.github.io/CUPiD/index.html#installing).

## Information on what is being run when running via CESM workflow
- Look at `helper_scripts/cesm_postprocessing.sh` for information on how CUPiD is run as part of the CESM workflow
- Look at `cime_config/config_tool.xml` for more detailed `env_postprocessing` xml variables

## Adjust CUPiD configuration within CESM
XML changes are a simple way to change the CUPiD configuration when you are running from CESM. See variables that you may want to adjust in your case directory with this query:
``` bash
./xmlquery -p CUPID
```

Adjust any variables that you would like (eg, the base case to compare against, how long to run for, etc) with the following command:
``` bash
./xmlchange <VARIABLE>=<VALUE>
```

Descriptions of XML variables and default values are in `CUPiD/cime_config/config_tool.xml`.

## Adjust wallclock time if needed
You can adjust the wallclock time for CUPiD specifically by running the following command:
``` bash
./xmlchange --subgroup case.cupid JOB_WALLCLOCK_TIME={new time}
```

You might want to do this if you are running an example with lots of computationally intensive diagnostic notebooks (for instance, a wallclock time of 6hr may be necessary for ILAMB).

## Adjust memory if needed
Change the memory required for running CUPiD as needed by running a command like the following:
``` bash
./xmlchange CUPID_MEM_PER_TASK={new memory [in GB]}
```

For instance, you may want to use 35 GB per task when running ILAMB. Note that the default is 10GB per task.

## How to run CUPiD
If you want to run CUPiD automatically after the short-term archiver finishes, you can run the following command from your case directory in order to turn on postprocessing:
``` bash
./xmlchange RUN_POSTPROCESSING=TRUE
```

Alternatively, in your case directory, you can also run CUPiD independently with this command after `case.st_archive` has completed:
``` bash
./case.submit --only-job case.cupid
```
