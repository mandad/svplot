import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import tiff_convert
# import optparse

def read_from_txt(filename):
    """Open a text file, tab separated"""
    try:
        sv_data = matplotlib.mlab.csv2rec(filename, delimiter='\t')
    except Exception, e:
        print "Input file could not be read." 
        raise SystemExit(1)

    #extract what we need
    xcoords = sv_data['x2']
    ycoords = sv_data['y2'] 
    sv_values = sv_data['ssp'].astype(np.float32)

    return (xcoords, ycoords, sv_values)

def calc_scaling_limits(values, method='hist', **kwargs):
    """Determines the limits for scaling colors in a plot"""
    # Determine SV range to scale colors
    # Allow command line specification of stdev range
    if method == 'stdev':
        sv_std_limit = float(kwargs['stdev'])
        # sv_std_limit = 2  # default to 2
        sv_stdev = np.std(values)
        sv_mean = np.mean(values)
        sv_min = max(sv_mean - (sv_std_limit * sv_stdev), np.min(values))
        sv_max = min(sv_mean + (sv_std_limit * sv_stdev), np.max(values))
    elif method == 'specified':
        sv_min = float(kwargs['min'])
        sv_max = float(kwargs['max'])
    elif method == 'minmax':
        sv_min = np.min(values)
        sv_max = np.max(values)
    else:
        if 'bins' in kwargs:
            bins = kwargs['bins']
        else:
            bins = 200
        sv_hist,bin_edges = np.histogram(values, bins=bins)
        sv_hist_masked = np.ma.masked_less(sv_hist, len(values) * 0.001)
        sv_limits = np.ma.flatnotmasked_edges(sv_hist_masked)
        sv_min = bin_edges[sv_limits[0]]
        sv_max = bin_edges[sv_limits[1]]

    if  sv_min == sv_max:
        sv_max = sv_min + 0.01

    return (sv_min, sv_max)

def plot_sv(xcoords, ycoords, sv_values, save_name, display_limits, utm_zone, show_hist=False):
    """Plots and saves maps of surface sound speed values"""
    # Determine x, y range for plot (so known)
    xlim_data = (np.min(xcoords), np.max(xcoords))
    ylim_data = (np.min(ycoords), np.max(ycoords))
    lim_scale = min(xlim_data[1] - xlim_data[0], ylim_data[1] - ylim_data[0]) * 0.1
    xlim_data = (xlim_data[0] - lim_scale, xlim_data[1] + lim_scale)
    ylim_data = (ylim_data[0] - lim_scale, ylim_data[1] + lim_scale)
    point_scale = 8000 / max(xlim_data[1] - xlim_data[0], ylim_data[1] - ylim_data[0])

    print 'Number of Data Points: ', len(sv_values)
    print 'Point Scale: ', point_scale
    print 'SV Range: ', display_limits[0], ' - ', display_limits[1] 

    normalize = matplotlib.colors.Normalize(vmin=display_limits[0], vmax=display_limits[1])

    # Make the figure
    fig = plt.figure(figsize=(12,8))
    ax = fig.add_subplot(111, aspect='equal', xlim=xlim_data, ylim=ylim_data) 
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    ax.set_axis_off()
    # print ax.axis()

    sc = ax.scatter(xcoords, ycoords, s=point_scale, c=sv_values, cmap='gist_rainbow', norm=normalize, edgecolors='none')

    # Save / Show map image
    fig.savefig(save_name, dpi=1000, bbox_inches='tight', pad_inches=0)

    # Save colorbar - specify whether alone or with map
    colorbar_map = False
    if colorbar_map:
        plt.colorbar(sc, format='%.1f')
        ax.set_axis_on()
    else:
        plt.close()

        fig = plt.figure(figsize=(2,6))

        ax = fig.add_axes([0.05,0.05,0.15,0.9])
        cb1 = matplotlib.colorbar.ColorbarBase(ax, cmap='gist_rainbow', norm=normalize, orientation='vertical', format='%.1f')
        cb1.set_label('Sound Velocity (m/s)')


    fig.savefig(save_name[:-4] + '_legend.png', dpi=300, bbox_inches='tight', pad_inches=0.2)
    plt.close()

    if show_hist:
        # Create a histogram
        plt.hist(sv_values, bins=30, range=(display_limits[0] - 1, display_limits[1] + 1)) #log=True for log scale
        plt.show()
        plt.close()

    # GDAL stuff
    tiff_convert.ConvertToGTiff(save_name, xlim_data, ylim_data, utm_zone) 

def main():
    if len(sys.argv) < 2:
        print ('Improper syntax - use:\n'
               'svplot.py txtfile zone [stdevs | sv_min sv_max]\n'
               '\n'
               'zone: UTM zone for the map\n' 
               'stdevs: Standard deviations around the mean for color scaling\n'
               'sv_min, sv_max: Specify absolute limits for color scaling\n'
               '\n'
               'If both are omitted, histogram scaling will be used.')
        raise SystemExit(1)

    xcoords, ycoords, sv_values = read_from_txt(sys.argv[1])
    save_name = sys.argv[1][:-3] + 'png'
    utm_zone = int(sys.argv[2])

    if len(sys.argv) == 4:
        scaling_limits = calc_scaling_limits(sv_values, 'stdev', stdev=sys.argv[3])
    elif len(sys.argv) == 5:
        scaling_limits = calc_scaling_limits(sv_values, 'specified', min=sys.argv[3], max=sys.argv[4])
    else:
        scaling_limits = calc_scaling_limits(sv_values, 'hist')

    plot_sv(xcoords, ycoords, sv_values, save_name, scaling_limits, utm_zone)


if __name__ == '__main__':
    main()