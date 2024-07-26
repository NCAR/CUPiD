from __future__ import annotations

import os

import numpy as np
import xarray as xr
from matplotlib import pyplot as plt
from netCDF4 import Dataset


def set_plot_prop_clean(ax):
    """
    This function cleans up the figures from unnecessary default figure properties.

    """
    ax.invert_yaxis()
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticklabels("")
    ax.set_yticklabels("")
    ax.set_xticks([])
    ax.set_yticks([])


def rmse(prediction, target):
    """
    This function returns the root mean square error for the SMB.
    Input:
        prediction = field to predict
        target = field to compare with the prediction
    """
    return np.sqrt(((prediction - target) ** 2).mean())


def net_avrg(data):
    """
    This function returns the net average of a data field
    """
    return np.sum(np.sum(data, axis=0), axis=0)


def read_smb(file):
    """
    This function reads the CISM SMB dataset from a CESM simulation output
    in the cpl directory. The output is adjusted to be converted to mm/yr w.e unit.

    Input:
        file: name of the file to extract the SMB
    """
    rhoi = 917  # ice density kg/m3
    sec_in_yr = 60 * 60 * 24 * 365  # seconds in a year
    smb_convert = sec_in_yr / rhoi * 1000  # converting kg m-2 s-1 ice to mm y-1 w.e.

    nid = Dataset(file, "r")
    smb_cism = np.squeeze(nid.variables["glc1Exp_Flgl_qice"][0, :, :]) * smb_convert
    nid.close()
    return smb_cism


def _get_cesm_output(path, case_name, last_year, params):
    # Set parameters
    rhoi = 917  # ice density kg/m3
    sec_in_yr = 60 * 60 * 24 * 365  # seconds in a year
    smb_convert = sec_in_yr / rhoi * 1000  # converting kg m-2 s-1 ice to mm y-1 w.e.

    filenames = []
    for k in range(params["climo_nyears"]):

        year_to_read = last_year - k
        filename = (
            f"{path}/{case_name}.cpl.hx.1yr2glc.{year_to_read:04d}-01-01-00000.nc"
        )

        if not os.path.isfile(filename):
            print(f"The couple file for time {year_to_read} does not exist.")
            print(
                "We will only use the files that existed until now to create the SMB climatology.",
            )
            break

        filenames.append(filename)

    climo_out = (
        xr.open_mfdataset(filenames)["glc1Exp_Flgl_qice"].compute() * smb_convert
    )
    # Mask out data that is 0 in initial condition
    for k in range(len(climo_out["time"])):
        climo_out.data[k, :, :] = np.where(
            params["mask"],
            0,
            climo_out.isel(time=k).data,
        )
    print("number of years used in climatology = ", len(climo_out["time"]))
    return climo_out


def create_climo(path, case_name, last_year, params):

    climo_out = _get_cesm_output(path, case_name, last_year, params)

    # Averaging the climo data
    return climo_out.mean("time").data


def compute_annual_climo(path, case_name, last_year, params):
    # Initializing a field for the climatology
    avg_smb_timeseries = np.zeros(last_year)
    climo_out = _get_cesm_output(path, case_name, last_year, params)
    for k in range(len(climo_out["time"])):
        # index into avg_smb_timeseries; want largest k to index (last_year-1)
        kk = last_year - (len(climo_out["time"]) - k)
        # note that mm_to_Gt has 1 / res**2 factor, so we want a sum rather than mean
        avg_smb_timeseries[kk] = np.round(
            climo_out.isel(time=k).sum() * params["mm_to_Gt"],
            2,
        ).data

    return last_year - len(climo_out["time"]) + 1, avg_smb_timeseries


def plot_contour(data, fig, ax, title, vmin, vmax, cmap, mm_to_Gt):
    avg_data = np.round(net_avrg(data) * mm_to_Gt, 2)
    last_panel0 = ax.imshow(data[:, :], vmin=vmin, vmax=vmax, cmap=cmap)
    ax.set_title(title, fontsize=16)
    set_plot_prop_clean(ax)
    ax.annotate("net avg =" + str(avg_data) + " Gt/yr", xy=(5, 5), fontsize=16)

    pos = ax.get_position()
    cax = fig.add_axes([0.35, pos.y0, 0.02, pos.y1 - pos.y0])

    cbar = fig.colorbar(last_panel0, cax=cax)
    cbar.ax.tick_params(labelsize=16)


def plot_contour_diff(data_new, data_old, fig, ax, title, vmin, vmax, cmap, mm_to_Gt):
    avg_data = np.round(net_avrg(data_new - data_old) * mm_to_Gt, 2)
    last_panel2 = ax.imshow(data_new - data_old, vmin=vmin, vmax=vmax, cmap=cmap)

    ax.set_title(title, fontsize=16)
    set_plot_prop_clean(ax)

    ax.annotate("net avg =" + str(avg_data) + " Gt/yr", xy=(5, 5), fontsize=16)

    pos = ax.get_position()
    cax = fig.add_axes([0.89, pos.y0, 0.02, pos.y1 - pos.y0])

    cbar = fig.colorbar(last_panel2, cax=cax)
    cbar.ax.tick_params(labelsize=16)


def plot_line(data, time, line, color, label, linewidth):
    plt.plot(
        time,
        data,
        line,
        ms=3,
        mfc=color,
        color=color,
        label=label,
        linewidth=linewidth,
    )
