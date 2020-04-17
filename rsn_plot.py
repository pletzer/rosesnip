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
    model, diag = bn[0], bn[1]
    return model, diag

def get_diag2model_map(ncfiles):
    d = {}
    for ncfile in ncfiles:
        model, diag = get_model_diag_from_filename(ncfile)
        d[diag] = d.get(diag, []).append((model, ncfile))
    return d

def get_time_series_data_from_netcdf_file(ncfile, model):
    nc = netCDF4.Dataset(ncfile, 'r')
    y = nc.variables[model][:]
    x = nc.variables['time'][:]
    nc.close()
    return x, y

def get_properties(conf_file, diag, model):
    props = {
        'marker_edge_color': 'k',
        'marker_face_color': 'r',
        'marker_style': 'x',
        'marker_size': 12,
        'line_color' : 'b',
        'line_width' : 1,
        'line_style' : '-',
    }
    cf = ConfigParser()
    cf.read(conf_file)
    diag_defn = cf['namelist:diags(' + diag + ')']
    for p in props:
        props[p] = diag_defn.get(p, props[p])
    return props


def main():
    parser = argparse.ArgumentParser(description='Plot results.')
    parser.add_argument('-c', dest='conf_filename', default='rose-app-expanded.conf', 
                           help='serial rose config file, for instance "rose-app-expanded.conf"')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory')
    args = parser.parse_args()

    if args.result_dir[0] != '/':
        # create absolute path
        args.result_dir = os.getcwd() + '/' + args.result_dir

    # find all the onetcdf files
    ncfiles = glob.glob(args.result_dir + '/nc/*.nc')


    # create list of diagnostics
    diag_map = get_diag2model_map(ncfiles)

    # generate plots, one for each diagnostic
    for diag, mf in diag_map.items():
        legs = []
        for model, ncfile in mf:
            x, y = get_time_series_data_from_netcdf_file(ncfile, model)
            props = get_properties(args.conf_filename, diag, model)
            pylab.plot(x, y, **props)
            legs.append(model)
        pylab.title(diag)
        pyalb.legend(legs)
        pylab.figsave(args.result_dir + '/images/{}_{}.png')


