import sys
import glob
import os.path
if sys.version_info.major < 3:
    raise RuntimeError('ERROR: Need python 3 but got python {}'.format(sys.version_info.major))
import argparse
# requires Python 3
from configparser import ConfigParser
import netCDF4
from matplotlib import pylab


def get_model_diag_from_filename(ncfile):
    bn = os.path.basename(ncfile).split('_')
    model, diag = bn[0], bn[2]
    return model, diag

def get_diag2model_map(ncfiles):
    d = {}
    for ncfile in ncfiles:
        model, diag = get_model_diag_from_filename(ncfile)
        v = d.get(diag, []) + [(model, ncfile)]
        d[diag] = v
    return d

def get_time_series_data_from_netcdf_file(ncfile, diag):
    nc = netCDF4.Dataset(ncfile, 'r')
    print(ncfile)
    yv = nc.variables[diag]
    xv = nc.variables['time']
    y = yv[:]
    x = xv[:]
    # attach attributes
    ylabel = getattr(yv, 'standard_name', '') + '[' + \
             getattr(yv, 'units', '-') + ']'
    xlabel = getattr(xv, 'standard_name', '') + '[' + \
             getattr(xv, 'units', '-') + ']'

    nc.close()
    return x, y, xlabel, ylabel


def main():
    parser = argparse.ArgumentParser(description='Plot results.')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory')
    args = parser.parse_args()

    if args.result_dir[0] != '/':
        # create absolute path
        args.result_dir = os.getcwd() + '/' + args.result_dir

    # find all the onetcdf files
    ncfiles = glob.glob(args.result_dir + '/nc/*.nc')
    print('Looking at netCDF files {}...'.format([os.path.basename(ncf) for ncf in ncfiles]))


    # create list of diagnostics
    diag_map = get_diag2model_map(ncfiles)
    print(diag_map)

    linetype = ['-', '-.', '--', ':', ]
    nline = len(linetype)

    # generate plots, one for each diagnostic
    for diag, mf in diag_map.items():
        legs = []

        count = 0
        for model, ncfile in mf:
            x, y, xlabel, ylabel = get_time_series_data_from_netcdf_file(ncfile, diag)
            pylab.plot(x, y, linetype[count % nline])
            legs.append(model)
            count += 1
        pylab.ylabel(ylabel)
        pylab.xlabel(xlabel)
        pylab.title(diag)
        pylab.legend(legs)
        pylab.savefig(args.result_dir + '/images/{}.png'.format(diag))


if __name__ == '__main__':
    main()