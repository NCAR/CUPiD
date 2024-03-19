# <img src="images/logo.png" alt="CUPiD Logo" width=100 /> CUPiD: CESM Unified Postprocessing and Diagnostics

Python Framework for Generating Diagnostics from CESM

## Project Vision

CUPiD is a collaborative effort that unifies all CESM component diagnostics and provides

- Python code that
  1. runs in an easy-to-generate conda environment, and
  1. can be launched via CIME workflow or independently
- Diagnostics for single/multiple runs and single/multiple components
- Ability to call post-processing tools that other groups are working on
- An API that makes it easy to include outside code
- Ongoing support and software maintenance

## Installing

To install CUPiD, you need to check out the code and then set up a few environments.
The initial examples have hard-coded paths that require you to be on `casper`.

The code relies on submodules to install `manage_externals` and then uses `manage_externals` for a few packages that are still being developed,
so the `git clone` process is a little more complicated than usual:

``` bash
$ git clone --recurse-submodules https://github.com/NCAR/CUPiD.git
$ cd CUPiD
$ ./manage_externals/checkout_externals
```

Then build the necessary conda environments with

``` bash
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
1. If `./manage_externals/checkout_externals` is not found, run `git submodule update --init` to clone the submodule.
1. If `which cupid-run` returned the error `which: no cupid-run in ($PATH)`, then please run the following:

``` bash
$ conda activate cupid-dev
$ pip install -e .  # installs cupid
```

## Running

CUPiD currently provides an example for generating diagnostics.
To test the package out, try to run `examples/coupled-model`:

``` bash
$ conda activate cupid-dev
$ cd examples/coupled_model
$ # machine-dependent: request multiple compute cores
$ cupid-run config.yml
$ cupid-build config.yml # Will build HTML from Jupyter Book
```

After the last step is finished, you can use Jupyter to view generated notebooks in `${CUPID_ROOT}/examples/coupled-model/computed_notebooks/quick-run`
or you can view `${CUPID_ROOT}/examples/coupled-model/computed_notebooks/quick-run/_build/html/index.html` in a web browser.

### CUPiD Options

Most of CUPiD's configuration is done via the `config.yml` file, but there are a few command line options as well:

```bash
(cupid-dev) $ cupid-run -h
Usage: cupid-run [OPTIONS] CONFIG_PATH

  Main engine to set up running all the notebooks.

Options:
  -s, --serial        Do not use LocalCluster objects
  -ts, --time-series  Run time series generation scripts prior to diagnostics
  -a, --all           Run all component diagnostics
  -atm, --atmosphere  Run atmosphere component diagnostics
  -ocn, --ocean       Run ocean component diagnostics
  -lnd, --land        Run land component diagnostics
  -ice, --seaice      Run sea ice component diagnostics
  -glc, --landice     Run land ice component diagnostics
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

If no component flags are provided, `--all` will be assumed and all component diagnostics listed in `config.yml` will be executed. Multiple flags can be used together to select a group of components, for example: `cupid-run -ocn -ice config.yml`.