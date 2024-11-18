# Running CUPiD on NCAR Supercomputers

A few tips and tricks tailored for the CISL's compute environment.

## Running in Parallel

There are two ways to request multiple cores on either casper or derecho.
Both cases are requesting 12 cores and 120 GB of memory.


The recommended approach releases the cores immediately after `cupid-run` finishes:

```
[login-node] $ conda activate cupid-dev
(cupid-dev) [login-node] $ qcmd -l select=1:ncpus=12:mem=120GB -- cupid-run
```

Alternatively, you can start an interactive session and remain on the compute nodes after `cupid-run` completes:

```
[login-node] $ qinteractive -l select=1:ncpus=12:mem=120GB
[compute-node] $ conda activate cupid-dev
(cupid-dev) [compute-node] $ cupid-run
```

Notes:
1. If you chose to run on derecho, specify the `develop` queue by adding the option `-q develop` to either `qcmd` or `qinteractive`
   (the `develop` queue is a shared resource and you are charged by the core hour rather than the node hour).
1. `cupid-build` is not computationally expensive, and can be run on a login node for either machine.

## Looking at Output

You can visualize the web page in a browser using the FastX service.
FastX requires you to be on the internal NCAR network (either on-site or via the VPN),
and can be accessed via the following steps:

1. Open a new browser window that points to https://fastx.ucar.edu:3300/session/
1. Open a default desktop icon.
1. Select the browser client.
1. Type `xterm` and hit enter to open a terminal.
1. In the terminal, run `cd ${CUPID_ROOT}/examples/coupled_model/computed_notebooks/quick-run/_build/html` to enter the `html` directory.
1. From the updated directory, run `firefox index.html &` to open a web browser pointed at the generated web page.
