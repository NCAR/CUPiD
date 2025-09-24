from __future__ import annotations

import numpy as np


def nmse(obs, mod):
    """Calculate the normalized mean squared error metric of Williamson (1995)
    "Skill Scores from the AMIP Simulations".
    nmse = overbar( (z_m - z_a)**2 ) / overbar( (z_a')**2 )
    where overbar is the weighted spatial average and prime is the deviation
    from that
    """

    # get the weights and weight by zero if the model or obs is nan
    w = np.cos(np.deg2rad(obs.lat))
    w = w.expand_dims({"lon": obs.lon}, axis=1)
    w = w.where(~(np.isnan(obs) | np.isnan(mod)), 0)
    obs = obs.where(w != 0, 0)
    mod = mod.where(w != 0, 0)

    # numerator
    num = (mod - obs) ** 2.0
    numw = num.weighted(w)
    numwm = numw.mean(["lon", "lat"])

    # denomenator
    obsw = obs.weighted(w)
    obswm = obsw.mean(["lon", "lat"])
    obsprime = obs - obswm
    obsprime2 = obsprime**2.0
    obsprime2w = obsprime2.weighted(w)
    obsprime2wm = obsprime2w.mean(["lon", "lat"])

    nmse = numwm / obsprime2wm

    return nmse
