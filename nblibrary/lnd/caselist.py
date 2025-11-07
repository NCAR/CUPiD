"""
A class for holding a list of cases and information about them
"""
from __future__ import annotations

import copy
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

    @classmethod
    def _create_empty(cls):
        """
        Create an empty CaseList without going through the normal initialization (i.e., import).
        Used internally by sel() and isel() for creating copies.
        """
        # Create instance without calling __init__
        instance = cls.__new__(cls)
        # Initialize as empty list
        list.__init__(instance)
        # Set minimal required attributes
        instance.names = []
        instance.resolutions = set()
        return instance

    def _copy_other_attributes(self, dest_case_list):
        """
        Copy all CaseList attributes from self to destination CaseList, skipping cft_ds.
        """
        for attr in [a for a in dir(self) if not a.startswith("__")]:
            if attr == "cft_ds":
                continue
            setattr(dest_case_list, attr, getattr(self, attr))
        return dest_case_list

    def sel(self, *args, **kwargs):
        """
        Loops through CaseList.cft_ds, applying Dataset.sel() with given arguments.
        """
        new_case_list = self._create_empty()

        # Copy each cft_ds one at a time for memory efficiency
        for case in self:
            # TODO: Might be more memory-efficient to not do this deep copy, instead copying
            # everything EXCEPT cft_ds.
            case_copy = copy.deepcopy(case)
            case_copy.cft_ds = case_copy.cft_ds.sel(*args, **kwargs)
            new_case_list.append(case_copy)

        # Copy over other attributes
        new_case_list = self._copy_other_attributes(new_case_list)
        return new_case_list

    def isel(self, *args, **kwargs):
        """
        Loops through CaseList.cft_ds, applying Dataset.isel() with given arguments.
        """
        new_case_list = self._create_empty()

        # Copy each cft_ds one at a time for memory efficiency
        for case in self:
            # TODO: Might be more memory-efficient to not do this deep copy, instead copying
            # everything EXCEPT cft_ds.
            case_copy = copy.deepcopy(case)
            case_copy.cft_ds = case_copy.cft_ds.isel(*args, **kwargs)
            new_case_list.append(case_copy)

        # Copy over other attributes
        new_case_list = self._copy_other_attributes(new_case_list)
        return new_case_list

    def sel_safer(self, *args, **kwargs):
        """
        As sel(), but may be easier to maintain as more attributes are added to CaseList. Tradeoff
        is that this is less memory-efficient.
        """
        new_case_list = copy.deepcopy(self)
        for case in new_case_list:
            case.cft_ds = case.cft_ds.sel(*args, **kwargs)
        return new_case_list

    def isel_safer(self, *args, **kwargs):
        """
        As isel(), but may be easier to maintain as more attributes are added to CaseList. Tradeoff
        is that this is less memory-efficient.
        """
        new_case_list = copy.deepcopy(self)
        for case in new_case_list:
            case.cft_ds = case.cft_ds.isel(*args, **kwargs)
        return new_case_list
