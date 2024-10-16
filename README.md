# <img src="images/logo.png" alt="CUPiD Logo" width=100 /> CUPiD: CESM Unified Postprocessing and Diagnostics

Python Framework for Generating Diagnostics from CESM

## Project Vision

CUPiD is a “one stop shop” that enables and integrates timeseries file generation, data standardization, diagnostics, and metrics from all CESM components.

This collaborative effort aims to simplify the user experience of running diagnostics by calling post-processing tools directly from CUPiD, running all component diagnostics from the same tool as either part of the CIME workflow or independently, and sharing python code and a standard conda environment across components.

## Installing

To install CUPiD, you need to check out the code and then set up a few environments.
The initial examples have hard-coded paths that require you to be on `casper`.

The code relies on submodules to install a few packages that are still being developed,
so the `git clone` process requires `--recurse-submodules`:

``` bash
$ git clone --recurse-submodules https://github.com/NCAR/CUPiD.git
```

Then `cd` into the `CUPiD` directory and build the necessary conda environments with

``` bash
$ cd CUPiD
$ mamba env create -f environments/dev-environment.yml
$ conda activate cupid-dev
$ which cupid-run
$ mamba env create -f environments/cupid-analysis.yml
```

Notes:

1. As of version 23.10.0, `conda` defaults to using `mamba` to solve environments.
It still feels slower than running `mamba` directly, hence the recommendation to install with `mamba env create` rather than `conda env create`.
If you do not have `mamba` installed, you can still use `conda`... it will just be significantly slower.
(To see what version of conda you have installed, run `conda --version`.)
1. If the subdirectories in `externals/` are all empty, run `git submodule update --init` to clone the submodules.
1. For existing users who cloned `CUPiD` prior to the switch from manage externals to git submodule, we recommend removing `externals/` before checking out main, running `git submodule update --init`, and removing `manage_externals` (if it is still present after `git submodule update --init`).
1. If `which cupid-run` returned the error `which: no cupid-run in ($PATH)`, then please run the following:

   ``` bash
   $ conda activate cupid-dev
   $ pip install -e .  # installs cupid
   ```

1. If you plan on contributing code to CUPiD,
whether developing CUPiD itself or providing notebooks for CUPiD to run,
please see the [Contributer's Guide](https://github.com/NCAR/CUPiD/wiki/Contributor's-Guide).
Note that CUPiD uses `pre-commit` to ensure code formatting guidelines are followed,
and pull requests will not be accepted if they fail the `pre-commit`-based Github Action.

## Running

CUPiD currently provides an example for generating diagnostics.
To test the package out, try to run `examples/coupled-model`:

``` bash
$ conda activate cupid-dev
$ cd examples/coupled_model
$ # machine-dependent: request multiple compute cores
$ cupid-run
$ cupid-build  # Will build HTML from Jupyter Book
```

After the last step is finished, you can use Jupyter to view generated notebooks in `${CUPID_ROOT}/examples/coupled-model/computed_notebooks/quick-run`
or you can view `${CUPID_ROOT}/examples/coupled-model/computed_notebooks/quick-run/_build/html/index.html` in a web browser.

Notes:

1. Occasionally users report the following error the first time they run CUPiD: `Environment cupid-analysis specified for <YOUR-NOTEBOOK>.ipynb could not be found`. The fix for this is the following:
   ``` bash
   $ conda activate cupid-analysis
   (cupid-analysis) $ python -m ipykernel install --user --name=cupid-analysis
   ```

Furthermore, to clear the `computed_notebooks` folder which was generated by the `cupid-run` and `cupid-build` commands, you can run the following command:

``` bash
$ cupid-clear
```

This will clear the `computed_notebooks` folder which is at the location pointed to by the `run_dir` variable in the `config.yml` file.

### CUPiD Options

Most of CUPiD's configuration is done via the `config.yml` file, but there are a few command line options as well:

```bash
(cupid-dev) $ cupid-run -h
Usage: cupid-run [OPTIONS] CONFIG_PATH

  Main engine to set up running all the notebooks.

Options:
  -s, --serial        Do not use LocalCluster objects
  -ts, --time-series  Run time series generation scripts prior to diagnostics
  -atm, --atmosphere  Run atmosphere component diagnostics
  -ocn, --ocean       Run ocean component diagnostics
  -lnd, --land        Run land component diagnostics
  -ice, --seaice      Run sea ice component diagnostics
  -glc, --landice     Run land ice component diagnostics
  --config_path       Path to the YAML configuration file containing specifications for notebooks (default config.yml)
  -h, --help          Show this message and exit.
```

#### Running in serial

By default, several of the example notebooks provided use a dask `LocalCluster` object to run in parallel.
However, the `--serial` option will pass a logical flag to each notebook that can be used to skip starting the cluster.

```py3
# Spin up cluster (if running in parallel)
client=None
if not serial:
  cluster = LocalCluster(**lc_kwargs)
  client = Client(cluster)

client
```

#### Specifying components

If no component flags are provided, all component diagnostics listed in `config.yml` will be executed by default. Multiple flags can be used together to select a group of components, for example: `cupid-run -ocn -ice`.


### Timeseries File Generation
CUPiD also has the capability to generate single variable timeseries files from history files for all components. To run timeseries, edit the `config.yml` file's timeseries section to fit your preferences, and then run `cupid-run -ts`.
