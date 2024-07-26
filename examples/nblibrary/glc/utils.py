from __future__ import annotations

import os

import numpy as np
import xarray as xr
from matplotlib import pyplot as plt


def read_cesm_smb(path, case_name, last_year, params):
    """
    This function reads CESM coupler history files and returns
    an xarray DataArray containing surface mass balance in units mm/y
    """
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


def plot_contour(da, fig, ax, title, vmin, vmax, cmap, mm_to_Gt):
    avg_data = np.round(da.sum().data * mm_to_Gt, 2)
    last_panel0 = ax.imshow(da.data[:, :], vmin=vmin, vmax=vmax, cmap=cmap)
    ax.set_title(title, fontsize=16)
    set_plot_prop_clean(ax)
    ax.annotate("net avg =" + str(avg_data) + " Gt/yr", xy=(5, 5), fontsize=16)

    pos = ax.get_position()
    cax = fig.add_axes([0.35, pos.y0, 0.02, pos.y1 - pos.y0])

    cbar = fig.colorbar(last_panel0, cax=cax)
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
