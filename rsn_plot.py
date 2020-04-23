import sys
import glob
import os.path
if sys.version_info.major < 3:
    raise RuntimeError('ERROR: Need python 3 but got python {}'.format(sys.version_info.major))
import argparse
# requires Python 3
from configparser import ConfigParser
from matplotlib import pylab
import iris
import iris.plot


def get_model_diag_statop_from_filename(ncfile):
    bn = os.path.basename(ncfile).split('_')
    model, diag = bn[0], bn[2]
    statop = os.path.basename(os.path.dirname(ncfile))
    return model, diag, statop

def get_diag2model_map(ncfiles):
    d = {}
    for ncfile in ncfiles:
        model, diag, statop = get_model_diag_statop_from_filename(ncfile)
        v = d.get(diag, []) + [(model, statop, ncfile)]
        d[diag] = v
    return d

def get_time_series_data_from_netcdf_file(ncfile, diag):
    cube = iris.load_cube(ncfile)
    t = cube.coords()[0]
    # attach attributes
    ylabel = repr(getattr(cube, 'standard_name', '')) + ' [' + \
             repr(getattr(cube, 'units', '-')) + ']'
    xlabel = repr(getattr(t, 'standard_name', '')) + ' [' + \
             repr(getattr(t, 'units', '-')) + ']'
    return cube, xlabel, ylabel


def main():
    parser = argparse.ArgumentParser(description='Plot results.')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory')
    parser.add_argument('-I', dest='interactive', action='store_true', 
                      help='create interactive plot')
    parser.add_argument('-l', dest='legend', action='store_true', 
              help='add legend')
    args = parser.parse_args()

    if args.result_dir[0] != '/':
        # create absolute path
        args.result_dir = os.getcwd() + '/' + args.result_dir

    # find all the netcdf files
    ncfiles = glob.glob(args.result_dir + '/nc/*/*.nc')
    print('Looking at netCDF files {}...'.format([os.path.basename(ncf) for ncf in ncfiles]))

    # create list of diagnostics
    diag_map = get_diag2model_map(ncfiles)
    print(diag_map)

    linetype = ['-', '-.', '--', ':', ]
    nline = len(linetype)

    # generate plots, one for each diagnostic
    for diag, msf in diag_map.items():
        legs = []

        count = 0
        for model, statop, ncfile in msf:
            cube, xlabel, ylabel = get_time_series_data_from_netcdf_file(ncfile, diag)
            iris.plot.plot(cube, linetype[count % nline])
            legs.append(model)
            count += 1
        pylab.ylabel(ylabel)
        pylab.xlabel(xlabel)
        pylab.title(diag)
        if args.interactive:
            pylab.show()
        else:
            image_dir = args.result_dir + '/images/' + statop
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)
            pylab.savefig('{}/{}.png'.format(image_dir, diag))


if __name__ == '__main__':
    main()
