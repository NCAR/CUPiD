from __future__ import annotations

import math

import numpy as np

# performance metrics


def remove_nan(qsim, qobs):
    sim_obs = np.stack((qsim, qobs), axis=1)
    sim_obs = sim_obs[~np.isnan(sim_obs).any(axis=1), :]
    return sim_obs[:, 0], sim_obs[:, 1]


def nse(qsim, qobs):
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return 1 - np.sum((qsim1 - qobs1) ** 2) / np.sum((qobs1 - np.mean(qobs1)) ** 2)


def corr(qsim, qobs):
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.corrcoef(qsim1, qobs1)[0, 1]


def alpha(qsim, qobs):
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return math.sqrt(np.sum((qsim1 - np.mean(qsim1)) ** 2) / len(qsim1)) / math.sqrt(
        np.sum((qobs1 - np.mean(qobs1)) ** 2) / len(qobs1),
    )


def beta(qsim, qobs):
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.mean(qsim1) / np.mean(qobs1)


def kge(qsim, qobs):
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return 1 - math.sqrt(
        (1 - corr(qsim1, qobs1)) ** 2
        + (alpha(qsim1, qobs1) - 1) ** 2
        + (beta(qsim1, qobs1) - 1) ** 2,
    )


def pbias(qsim, qobs):
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.sum(qsim1 - qobs1) / np.sum(qobs1)


def mae(qsim, qobs):
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.sum(abs(qsim1 - qobs1)) / np.sum(qobs1)


def rmse(qsim, qobs):
    qsim1, qobs1 = remove_nan(qsim, qobs)
    return np.sqrt(np.mean((qsim1 - qobs1) ** 2))
