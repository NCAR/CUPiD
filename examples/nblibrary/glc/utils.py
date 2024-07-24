from __future__ import annotations

import os

import numpy as np
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


def create_climo(path, case_name, last_year, params):
    # Initializing a field for the climatology
    climo_out = np.zeros((params["ny_cism"], params["nx_cism"]))

    # Counter for available year (only needed if the number of years available is smaller
    # than the number of years requested to create the climatology.
    count_yr = 0

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

        climo_out = climo_out + read_smb(filename)
        count_yr = count_yr + 1

    print("number of years used in climatology = ", count_yr)
    # Averaging the climo data
    return climo_out / count_yr


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


def compute_annual_climo(path, case_name, last_year, params):
    # Initializing a field for the climatology
    avg_smb_timeseries = np.zeros(last_year)

    # Counter for available year (only needed if the number of years available is smaller
    # than the number of years requested to create the climatology.
    count_yr = 0

    for k in range(last_year):

        year_to_read = last_year - k
        file_name = (
            f"{path}/{case_name}.cpl.hx.1yr2glc.{year_to_read:04d}-01-01-00000.nc"
        )

        if not os.path.isfile(file_name):
            print("The couple file for time", year_to_read, "does not exist.")
            print(
                "We will only use the files that existed until now to create the time series.",
            )
            break

        smb_temp = read_smb(file_name)
        smb_temp = np.where(params["mask"], 0, smb_temp)

        avg_smb_timeseries[year_to_read - 1] = np.round(
            net_avrg(smb_temp) * params["mm_to_Gt"],
            2,
        )
        count_yr = count_yr + 1

        if count_yr == params["climo_nyears"]:
            break

        del smb_temp

    first_year = year_to_read

    print("number of years used in climatology = ", count_yr)
    return first_year, avg_smb_timeseries


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
