# + tags=["parameters"]
# add default values for parameters here

# +
import os

print(os.environ['CONDA_DEFAULT_ENV'])

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mpath
from matplotlib.gridspec import GridSpec
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import nc_time_axis
import cftime

# +
def pop_div(x_e,y_n,dxt,dyt,tarea):
    x_e = x_e*dyt
    y_n = y_n*dxt
    x_w = x_e.roll(nlon=1,roll_coords=False)
    y_s = y_n.shift(nlat=1)
    div = (x_e-x_w+y_n-y_s)/tarea
    return div 


# -

print(dummy)

case1 = "g.e22.GOMIPECOIAF_JRA-1p4-2018.TL319_g17.4p2z.002branch"
var1 = "U1_1"
var2 = "V1_1"
vartitle = "POP Surface Current"
intv = 3

climo_path = "/glade/derecho/scratch/dbailey/archive/"+case1+"/ocn/proc/tseries/day_1/"

ds1 = xr.open_dataset(climo_path+case1+".pop.h.nday1."+var1+".20080102-20211231.nc")
ds2 = xr.open_dataset(climo_path+case1+".pop.h.nday1."+var2+".20080102-20211231.nc")

grid = xr.open_dataset("/glade/campaign/cesm/community/omwg/grids/gx1v7_grid.nc")
TLAT = grid['ULAT']
TLON = grid['ULONG']
angle = grid['ANGLE']
tarea = grid['TAREA']
dxt = grid['DXT']
dyt = grid['DYT']

uvel1 = ds1[var1][-1::,:,:].mean(axis=0)
vvel1 = ds2[var2][-1::,:,:].mean(axis=0)

uvel_rot1 = uvel1*np.cos(angle)-vvel1*np.sin(angle)
vvel_rot1 = uvel1*np.sin(angle)+vvel1*np.cos(angle)
#uvel_rot2 = uvel2*np.cos(angle)-vvel2*np.sin(angle)
#vvel_rot2 = uvel2*np.sin(angle)+vvel2*np.cos(angle)

div = pop_div(uvel1,vvel1,dxt,dyt,tarea)

print(div)

# var_diff = var1-var2
# var_std = var_diff.std()
# var_max = 5.
# var_min = 0.

# make circular boundary for polar stereographic circular plots
theta = np.linspace(0, 2*np.pi, 100)
center, radius = [0.5, 0.5], 0.5
verts = np.vstack([np.sin(theta), np.cos(theta)]).T
circle = mpath.Path(verts * radius + center)

# set up the figure with a North Polar Stereographic projection
fig = plt.figure(figsize=(10,10))
gs = GridSpec(1,1)

ax = fig.add_subplot(gs[0,0], projection=ccrs.NorthPolarStereo())
ax.set_boundary(circle, transform=ax.transAxes)
ax.add_feature(cfeature.LAND,zorder=100,edgecolor='k')

# sets the latitude / longitude boundaries of the plot
ax.set_extent([0.005, 360, 90, 55], crs=ccrs.PlateCarree())

this=ax.pcolormesh(TLON[:,:].values,
                   TLAT[:,:].values,
                   div.values,
                   cmap='rainbow',transform=ccrs.PlateCarree())

this=ax.quiver(TLON[::intv,::intv].values,
               TLAT[::intv,::intv].values,
               uvel_rot1[::intv,::intv].values,
               vvel_rot1[::intv,::intv].values,
               transform=ccrs.PlateCarree())

plt.savefig('vector.png')

# + [markdown]
# plt.colorbar(this,orientation='vertical',fraction=0.04,pad=0.01)
# plt.title(vartitle,fontsize=10)

