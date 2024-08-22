from matplotlib.colors import LinearSegmentedColormap
import matplotlib as mpl

# create colormaps
# ---------------
cmap11 = LinearSegmentedColormap.from_list('custom blue', 
                                           [(0,     'xkcd:red'),
                                            (0.05,  'xkcd:orange'),
                                            (0.50,  'xkcd:light grey'),
                                            (0.65,  'xkcd:sky blue'),
                                            (1,     'xkcd:blue')], N=15)

cmap12 = LinearSegmentedColormap.from_list('custom blue', 
                                           [(0,     'xkcd:light sky blue'),
                                            (0.25,  'xkcd:cyan'),
                                            (0.75,  'xkcd:blue'),
                                            (1,     'xkcd:royal blue')], N=8)
cmap12.set_under('red')


# kge
#vals0=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
#cmap0 = cm.get_cmap('plasma_r', (8))
#cmap0.set_under('cyan')
#cmap = mpl.colors.ListedColormap(mpl.cm.Spectral_r(np.arange(9)))
#norm0 = mpl.colors.BoundaryNorm(vals0, cmap0.N)
cmap0 = mpl.cm.plasma_r
cmap0.set_under('cyan')
vals0 = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
norm0 = mpl.colors.BoundaryNorm(vals0, cmap0.N, extend='both')


# %bias
vals1=[-0.5, -0.4, -0.3, -0.2, -0.1, 0.1, 0.2, 0.3, 0.4, 0.5]
cmap1 = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0, 'xkcd:red'),
                                              (0.5, 'xkcd:light grey'),
                                              (1.0, 'xkcd:blue')], N=11)
cmap1.set_over('xkcd:dark blue')
cmap1.set_under('xkcd:dark red')
norm1 = mpl.colors.BoundaryNorm(vals1, cmap1.N)


# ratio
vals2=[0.75, 0.8, 0.85, 0.9, 0.95, 1.05, 1.1, 1.15, 1.2, 1.25] 
#cmap = cm.get_cmap('RdYlBu', (7))
cmap2 = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0, 'xkcd:red'),
                                              (0.5, 'xkcd:light grey'),
                                              (1.0, 'xkcd:blue')], N=11)
cmap2.set_over('xkcd:dark blue')
cmap2.set_under('xkcd:dark red')
norm2 = mpl.colors.BoundaryNorm(vals2, cmap2.N)

# corr
vals3=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9] 
cmap3 = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.00, 'xkcd:yellow'),
                                              (0.50, 'xkcd:green'),
                                              (1.00, 'xkcd:blue')], N=8)
cmap3.set_over('xkcd:dark blue')
cmap3.set_under('xkcd:brown')
norm3 = mpl.colors.BoundaryNorm(vals3, cmap3.N)


# KGE difference
vals4=[-0.1, -0.08, -0.06, -0.04, -0.02, 0.02, 0.04, 0.06, 0.08, 0.1]
cmap4 = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0, 'xkcd:red'),
                                              (0.5, 'xkcd:light grey'),
                                              (1.0, 'xkcd:blue')], N=11)
cmap4.set_over('xkcd:royal blue')
cmap4.set_under('xkcd:magenta')
norm4 = mpl.colors.BoundaryNorm(vals4, cmap4.N)


cmap_summa_diff = LinearSegmentedColormap.from_list('custom 1', 
                                             [(0,    'xkcd:red'),
                                              (0.50, 'xkcd:light grey'),
                                              (1,    'xkcd:blue')], N=250)

cmap_summa_swe_diff = LinearSegmentedColormap.from_list('custom 2', 
                                             [(0,    'xkcd:red'),
                                              (0.50, 'xkcd:pale salmon'),
                                              (1,    'xkcd:light grey')], N=250)

# ---------------------
# climate change signal
# ---------------------

# annual centroid day change from control period
cmap_centroid_diff = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0, 'xkcd:red'),
                                              (50/60, 'xkcd:white'),
                                              (1.0, 'xkcd:blue')], N=255)
cmap_centroid_diff.set_over('xkcd:dark blue')
cmap_centroid_diff.set_under('xkcd:dark red')
norm_centroid_diff = mpl.colors.Normalize(vmin=-50, vmax=10)

# --------
# annual maximum date change from control period
cmap_max_day_diff = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0, 'xkcd:red'),
                                              (60/80, 'xkcd:white'),
                                              (1.0, 'xkcd:blue')], N=255)
cmap_max_day_diff.set_over('xkcd:dark blue')
cmap_max_day_diff.set_under('xkcd:dark red')
norm_max_day_diff = mpl.colors.Normalize(vmin=-60, vmax=20)

# --------
# annual minimum date change from control period
cmap_min_day_diff = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0,    'xkcd:red'),
                                              (50/150, 'xkcd:white'),
                                              (1.0,    'xkcd:blue')], N=255)
cmap_min_day_diff.set_over('xkcd:dark blue')
cmap_min_day_diff.set_under('xkcd:dark red')
norm_min_day_diff = mpl.colors.Normalize(vmin=-50, vmax=100)

# --------
# annual maximum flow change from control period
# cms
cmap_max_flow_diff = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0,      'xkcd:red'),
                                              (100/1600, 'xkcd:white'),
                                              (1.0,      'xkcd:blue')], N=255)
cmap_max_flow_diff.set_over('xkcd:dark blue')
cmap_max_flow_diff.set_under('xkcd:dark red')
norm_max_flow_diff=mpl.colors.Normalize(vmin=-100, vmax=1500)

# percent diff
cmap_max_flow_pdiff = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0,      'xkcd:red'),
                                              (20/70, 'xkcd:white'),
                                              (1.0,      'xkcd:blue')], N=255)
cmap_max_flow_pdiff.set_over('xkcd:dark blue')
cmap_max_flow_pdiff.set_under('xkcd:dark red')
norm_max_flow_pdiff=mpl.colors.Normalize(vmin=-20, vmax=50)

# annual maximum flow
norm_max_flow = mpl.colors.LogNorm(vmin=20, vmax=15000)

# --------
# annual minmum flow change from control period
cmap_min_flow_diff=LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0, 'xkcd:red'),
                                              (20/520, 'xkcd:white'),
                                              (1.0, 'xkcd:blue')], N=255)
cmap_min_flow_diff.set_over('xkcd:dark blue')
cmap_min_flow_diff.set_under('xkcd:dark red')
norm_min_flow_diff=mpl.colors.Normalize(vmin=-20, vmax=500)
# annual minimum flow
norm_min_flow = mpl.colors.LogNorm(vmin=1, vmax=2000)

# --------
# freq_high_q per yr
vals1=[-4, -3, -2, -1, 0, 1, 2, 3, 4]
cmap_freq_high_q_diff = LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0, 'xkcd:red'),
                                              (0.5, 'xkcd:white'),
                                              (1.0, 'xkcd:blue')], N=10)
cmap_freq_high_q_diff.set_over('xkcd:dark blue')
cmap_freq_high_q_diff.set_under('xkcd:dark red')
norm_freq_high_q_diff = mpl.colors.BoundaryNorm(vals1, cmap_freq_high_q_diff.N)
norm_freq_high_q = mpl.colors.Normalize(vmin=0, vmax=10)

# --------
# mean_high_q_duration per yr
cmap_freq_high_dur_diff=LinearSegmentedColormap.from_list('custom1', 
                                             [(0.0, 'xkcd:red'),
                                              (10/20, 'xkcd:white'),
                                              (1.0, 'xkcd:blue')], N=255)
cmap_freq_high_dur_diff.set_over('xkcd:dark blue')
cmap_freq_high_dur_diff.set_under('xkcd:dark red')
norm_freq_high_dur_diff=mpl.colors.Normalize(vmin=-10, vmax=10)
norm_freq_high_dur = mpl.colors.Normalize(vmin=0, vmax=20)
