"""
A class for holding a list of cases and information about them
"""
from __future__ import annotations

import os
from time import time


class CaseList(list):
    """
    A class for holding a list of cases and information about them
    """

    def __init__(
        self,
        *args,
        CropCase,
        identify_resolution,
        opts,
    ):
        # Initialize as a normal list...
        super().__init__(*args)
        # ...And then add all the extra stuff

        # Define extra variables
        self.names = opts["case_name_list"]

        # Import cases
        self._import_cases(
            CropCase,
            identify_resolution,
            opts,
        )
        self.resolutions = {case.cft_ds.attrs["resolution"] for case in self}

    def _import_cases(
        self,
        CropCase,  # pylint: disable=invalid-name
        identify_resolution,
        opts,
    ):
        start = time()
        for case_name in self.names:
            print(f"Importing {case_name}...")
            case_output_dir = os.path.join(
                opts["CESM_output_dir"],
                case_name,
                "lnd",
                "hist",
            )
            self.append(
                CropCase(
                    case_name,
                    case_output_dir,
                    opts["cfts_to_include"],
                    opts["crops_to_include"],
                    opts["start_year"],
                    opts["end_year"],
                    verbose=opts["verbose"],
                    force_new_cft_ds_file=opts["force_new_cft_ds_file"],
                    force_no_cft_ds_file=opts["force_no_cft_ds_file"],
                ),
            )

            # Get resolution
            self[-1].cft_ds.attrs["resolution"] = identify_resolution(
                self[-1].cft_ds,
            ).name

        print("Done.")
        if opts["verbose"]:
            end = time()
            print(f"Importing took {int(end - start)} s")
