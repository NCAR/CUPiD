#!/usr/bin/env python
"""
Main script for running GenTS to generate timeseries for all components
"""

import glob
import os

import click
from gents.hfcollection import HFCollection
from gents.timeseries import TSCollection

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# fmt: off
# pylint: disable=line-too-long


@click.command(context_settings=CONTEXT_SETTINGS)
def run_GenTS(
    dout_s_root="/glade/derecho/scratch/mlevy/GenTS_test/input",
    ts_outdir="/glade/derecho/scratch/mlevy/GenTS_test/output",
):
    config = {}
    config["atmos"] = {
        "include_patterns": ["*cam.h0a*"],
        "frequency": "mon",
        "subdir": "atm",
    }
    config["land"] = {
        "include_patterns": ["*clm2.h0a*"],
        "frequency": "mon",
        "subdir": "lnd",
    }
    # TODO: include ocn_grid_file and ocn_static_file
    # config["ocean"] = {"include_patterns": ["*mom6.h.native.*"],
    #                    "frequency": "mon",
    #                    "subdir": "ocn"}

    # TODO: spin up dask here
    client = None

    for _, setup in config.items():
        cnt = 0
        indir = os.path.join(dout_s_root, setup["subdir"], "hist")
        outdir = os.path.join(ts_outdir, setup["subdir"], "proc")
        print(f"outdir = {outdir}")
        for include_pattern in setup["include_patterns"]:
            cnt = cnt + len(glob.glob(os.path.join(indir, include_pattern)))
        hf_collection = HFCollection(indir, dask_client=client)
        for include_pattern in setup["include_patterns"]:
            print(f"Processing files with pattern: {include_pattern}")
            hfp_collection = hf_collection.include_patterns([include_pattern])
            hfp_collection.pull_metadata()
            ts_collection = TSCollection(
                hfp_collection, outdir, ts_orders=None, dask_client=client,
            )
            ts_collection.execute()


if __name__ == "__main__":
    run_GenTS()
