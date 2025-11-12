from __future__ import annotations

import os

import numpy as np
import xarray as xr
from matplotlib import pyplot as plt


def read_cesm_smb(path, case_name, last_year, climo_nyears, params):
    """
    This function reads CESM coupler history files and returns
    an xarray DataArray containing surface mass balance in units mm/y
    """
    # Set parameters
    rhoi = 917  # ice density kg/m3
    sec_in_yr = 60 * 60 * 24 * 365  # seconds in a year
    smb_convert = sec_in_yr / rhoi * 1000  # converting kg m-2 s-1 ice to mm y-1 w.e.

    filenames = []
    for k in range(climo_nyears):

        year_to_read = last_year - k
        filename = (
            f"{path}/{case_name}.cpl.hx.1yr2glc.{year_to_read:04d}-01-01-00000.nc"
        )

        if not os.path.isfile(filename):
            print(
                f"Looked for {filename} (for time {year_to_read}) but it does not exist.",
            )
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


# -------------------- #
#  PLOTTING FUNCTIONS  #
# -------------------- #


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


def plot_contour(da, fig, ax, left, title, vmin, vmax, cmap, mm_to_Gt):
    """
    Plot a contour map of surface mass balance (assumed to be in da.data).
    Also computes global mean, in Gt, and prints average in lower left corner.
    Arguments:
        da - xr.DataArray containing SMB in units of mm/yr
        fig - matplotlib.figure.Figure
        ax - matplotlib.axes.Axes
        left - left dimension of rect (dimensions for colorbar)
        title - string containing title of plot
        vmin - minimum value for contours
        vmax - maximum value for contours
        cmap - matplotlib.colors.Colormap
        mm_to_Gt - conversion factor for mm/yr -> Gt/yr
    """
    avg_data = np.round(da.sum().data * mm_to_Gt, 2)
    last_panel = ax.imshow(da.data[:, :], vmin=vmin, vmax=vmax, cmap=cmap)
    ax.set_title(title, fontsize=16)
    set_plot_prop_clean(ax)
    ax.annotate("net avg =" + str(avg_data) + " Gt/yr", xy=(5, 5), fontsize=16)

    pos = ax.get_position()
    cax = fig.add_axes([left, pos.y0, 0.02, pos.y1 - pos.y0])

    cbar = fig.colorbar(last_panel, cax=cax)
    cbar.ax.tick_params(labelsize=16)


def plot_line(da, time, line, color, label, linewidth):
    """
    Plot a time series of spatially averaged surface mass balance (assumed to
    be in da.data).
    Arguments:
        da - xr.DataArray containing spatially averaged SMB in units of Gt/yr
        time - np.array containing time dimension
        line - style of line to use in plot
        color - color of line in plot
        label - label of line in legend
        linewidth - thickness of line in plot
    """
    plt.plot(
        time,
        da,
        line,
        ms=3,
        mfc=color,
        color=color,
        label=label,
        linewidth=linewidth,
    )
