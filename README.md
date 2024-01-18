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

```
$ git clone --recurse-submodules https://github.com/NCAR/CUPiD.git
$ cd CUPiD
$ ./manage_externals/checkout_externals
```

Then build the necessary conda environments with

```
$ conda env create -f cupid/dev-environment.yml
$ conda activate cupid-dev
$ which cupid-run
$ conda env create -f cupid-analysis.yml
```

Notes:

1. `conda` now defaults to using `mamba` to solve environments; the `cupid-analysis.yml` environment is complicated, so older versions of `conda` should be updated (`conda update -n base conda`) or you should use `mamba` instead.
1. If `./manage_externals/checkout_externals` is not found, run `git submodule update --init` to clone the submodule.
1. If `which cupid-run` returned the error `which: no cupid-run in ($PATH)`, then please run the following:

```
$ conda activate cupid-dev
$ pip install -e .  # installs cupid
```

## Running

CUPiD currently provides two examples for generating diagnostics.
To test the package out, try to run `examples/coupled-model`:

```
$ conda activate cupid-dev
$ cd examples/coupled-model
$ cupid-run config.yml
$ cupid-build config.yml # Will build HTML from Jupyter Book
```

After the last step is finished, you can use Jupyter to view generated notebooks in `${CUPID_ROOT}/examples/coupled-model/computed_notebooks/quick-run`
or you can copy the entire `${CUPID_ROOT}/examples/coupled-model/computed_notebooks/quick-run/_build/html`
directory to your local machine and look at `index.html` in a web browser.
