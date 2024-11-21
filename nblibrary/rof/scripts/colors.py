from __future__ import annotations

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

# create colormaps
# ---------------
cmap_RedGrayBlue = LinearSegmentedColormap.from_list(
    "custom blue",
    [
        (0, "xkcd:red"),
        (0.05, "xkcd:orange"),
        (0.50, "xkcd:light grey"),
        (0.65, "xkcd:sky blue"),
        (1, "xkcd:blue"),
    ],
    N=15,
)

# %bias
vals_pbias = [-50, -40, -30, -20, -10, 10, 0.2, 30, 40, 50]
cmap_pbias = LinearSegmentedColormap.from_list(
    "custom1",
    [(0.0, "xkcd:red"), (0.5, "xkcd:light grey"), (1.0, "xkcd:blue")],
    N=11,
)
cmap_pbias.set_over("xkcd:dark blue")
cmap_pbias.set_under("xkcd:dark red")
norm_pbias = mpl.colors.BoundaryNorm(vals_pbias, cmap_pbias.N)


# corr
vals_corr = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
cmap_corr = LinearSegmentedColormap.from_list(
    "custom1",
    [(0.00, "xkcd:yellow"), (0.50, "xkcd:green"), (1.00, "xkcd:blue")],
    N=9,
)
cmap_corr.set_over("xkcd:dark blue")
cmap_corr.set_under("xkcd:brown")
norm_corr = mpl.colors.BoundaryNorm(vals_corr, cmap_corr.N)
