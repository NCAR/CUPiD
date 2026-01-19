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
$ mamba env create -f environments/cupid-infrastructure.yml
$ conda activate cupid-infrastructure
$ which cupid-diagnostics
$ mamba env create -f environments/cupid-analysis.yml
```

Notes:

1. As of version 23.10.0, `conda` defaults to using `mamba` to solve environments.
It still feels slower than running `mamba` directly, hence the recommendation to install with `mamba env create` rather than `conda env create`.
If you do not have `mamba` installed, you can still use `conda`... it will just be significantly slower.
(To see what version of conda you have installed, run `conda --version`.)
1. If the subdirectories in `externals/` are all empty, run `git submodule update --init` to clone the submodules.
1. For existing users who cloned `CUPiD` prior to the switch from manage externals to git submodule, we recommend removing `externals/` before checking out main, running `git submodule update --init`, and removing `manage_externals` (if it is still present after `git submodule update --init`).
1. If `which cupid-diagnostics` returned the error `which: no cupid-diagnostics in ($PATH)`, then please run the following:

   ``` bash
   $ conda activate cupid-infrastructure
   $ pip install -e .  # installs cupid
   ```

1. In the `cupid-infrastructure` environment, run `pre-commit install` to configure `git` to automatically run `pre-commit` checks when you try to commit changes from the `cupid-infrastructure` environment; the commit will only proceed if all checks pass. Note that CUPiD uses `pre-commit` to ensure code formatting guidelines are followed, and pull requests will not be accepted if they fail the `pre-commit`-based Github Action.
1. If you plan on contributing code to CUPiD,
whether developing CUPiD itself or providing notebooks for CUPiD to run,
please see the [Contributor's Guide](https://ncar.github.io/CUPiD/contributors_guide.html).


CUPiD can be run either as a [standalone tool](https://ncar.github.io/CUPiD/run_standalone.html) or via the [CESM workflow](https://ncar.github.io/CUPiD/run_cesm.html).

### Note:
Occasionally users report the following error the first time they run CUPiD: `Environment cupid-analysis specified for <YOUR-NOTEBOOK>.ipynb could not be found`. The fix for this is the following:
   ``` bash
   $ conda activate cupid-analysis
   (cupid-analysis) $ python -m ipykernel install --user --name=cupid-analysis
   ```
If you have an existing conda environment and want to update it, you can remove it and then follow the general installation instructions, eg:
   ``` bash
   (cupid-analysis) $ conda deactivate
   $ conda env remove -n cupid-analysis
   $ mamba env create -f environments/cupid-analysis.yml
   ```
