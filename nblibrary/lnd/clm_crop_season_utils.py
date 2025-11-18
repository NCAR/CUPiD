"""
Useful functions for calculations related to CLM crop growing seasons
"""
from __future__ import annotations

import os
import sys

externals_path = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    "externals",
)
sys.path.append(externals_path)
# pylint: disable=wrong-import-position,import-error

from ctsm_postprocessing.crops import combine_cft_to_crop  # noqa: E402

# Southern Hemisphere "overwintering" means spanning Jul. 1/2
SH_MIDWINTER_DOY = 182.5


def cft_ds_overwintering(cft_ds):
    """
    Calculate overwintering for each calendar year's harvests
    """

    # Whether the crop is in the Northern or Southern Hemisphere
    is_nh = cft_ds["pfts1d_lat"] >= 0

    # If Northern, "overwintering" means spanning Dec. 31/Jan. 1
    nh_overwinter = is_nh & (cft_ds["HDATES"] < cft_ds["SDATES_PERHARV"])
    sh_overwinter = (
        ~is_nh
        & (cft_ds["SDATES_PERHARV"] < SH_MIDWINTER_DOY)
        & (cft_ds["HDATES"] > SH_MIDWINTER_DOY)
    )

    # Save
    overwinter = (nh_overwinter | sh_overwinter) & (
        cft_ds["HARVEST_REASON_PERHARV"] > 0
    )
    cft_ds["overwinter_area"] = (overwinter * cft_ds["cft_harv_area"]).sum(
        dim="mxharvests",
    )
    cft_ds = combine_cft_to_crop.combine_cft_to_crop(
        cft_ds,
        "overwinter_area",
        "overwinter_area_crop",
        method="sum",
    )

    # Add units
    # TODO: This should be changed to happen automatically elsewhere!
    cft_ds["overwinter_area_crop"].attrs["units"] = "m2"

    return cft_ds
