# <img src="images/logo.png" alt="CUPiD Logo" width=100 /> CUPiD: CESM Unified Postprocessing and Diagnostics
Python Framework for Generating Diagnostics from CESM

## Project Vision
- Framework that can be launched via CIME workflow or on its own
- Run in an easy-to-generate conda environment
- Diagnostics for single/multiple runs and single/multiple components
- Incorporate postprocessing that other groups are working on
- API to make it easy to support outside code
- Provide ongoing support and software maintenance

## Installing

To install CUPiD, you need to check out the code and then set up a few environments.
The code relies on submodules to install `manage_externals` and then uses `manage_externals` for one more package,
so the `git clone` process is a little more complicated than usual:

```
$ git clone --recurse-submodules https://github.com/NCAR/CUPiD.git
$ cd CUPiD
$ ./manage_externals/checkout_externals
```

Then build the necessary conda environments with

```
$ mamba env create -f nbscuid/dev-environment.yml
$ mamba env create -f mom6-environment.yml
```

## Running

CUPiD currently provides two examples for generating diagnostics.
To test the package out, try to run `examples/adf-mom6`:

```
$ cd examples/adf-mom6
$ conda activate nbscuid-dev
$ nbscuid-run config.yml
$ nbscuid-build config.yml # Will build HTML from Jupyter Book
```
