import sys
if sys.version_info.major < 3:
    raise RuntimeError('ERROR: Need python 3 but got python {}'.format(sys.version_info.major))
import argparse
# requires Python 3
from configparser import ConfigParser
import os
import re
from datetime import datetime
import copy
import numpy
from configparser impoert ConfigParser

"""
Prepare micro rose configuration files for parallel processing
"""

# regex pattern for diag sections
PAT_DIAG = re.compile(r'namelist:diags\(([^\)]+)\)')
# regex pattern for model sections
PAT_MODEL = re.compile(r'namelist:models\(([^\)]+)\)')


def get_year(dt):
    """Extract the year from YYYY-MM-DD*"""
    return int(dt.split('-')[0])

def get_month_day(dt):
    """Extract the month and day from YYYY-MM-DD-*"""
    return dt.split('-')[1:3]

def split_time_range(start_date, end_date, steps=1):
    """
    Split a time range into n segments

    start_date : start date in YYYY-MM-DD format
    end_date   : end date in YYYY-MM-DD format
    steps      : number of years between start/end 

    returns a list [start_date0, start_date1, ....]
    """
    start_year = get_year(start_date)
    end_year = get_year(end_date)
    years = numpy.arange(start_year, end_year + 1)   
    nchunks = max(1, (end_year - start_year) // steps)
    chunks = [x for x in numpy.array_split(years, nchunks) if x.size > 0]
    res = [str(c[0]) + '-01-01' for c in chunks]
    res[0] = start_date
    res.append(end_date)

    return res


def generate_template_conf(rose_conf, result_dir):
    """
    Returns a template configuration without models or diags

    rose_conf  : original rose configuration

    returns template configuration
    """
    conf = ConfigParser()
    for section in rose_conf.sections():
        if not re.match(PAT_MODEL, section) and not re.match(PAT_DIAG, section):
            # not a model and not a diag section so add
            conf[section] = rose_conf[section]

    # set the result_dir
    conf['general']['output_dir'] = result_dir

    return conf 


def create_model_diag_conf(rose_conf, templ_conf, model, diag, index, start_date='', end_date=''):
    """
    Add model and diag sections to configuration

    rose_conf   : original rose configuration
    templ_conf  : template configuration, will be copied
    model       : model name
    diag        : diag name
    index       : processor id
    start_date  : start date to add to model section
    end_date    : end date to add to model section

    returns a configuration
    """

    conf = copy.deepcopy(templ_conf)

    mname = 'namelist:models(' + model + ')'
    dname = 'namelist:diags(' + diag + ')'
    conf[mname] = rose_conf[mname]
    conf[dname] = rose_conf[dname]

    # set the start and send dates (if defined)
    if start_date:
        conf[mname]['start_date'] = start_date
    if end_date:
        conf[mname]['end_date'] = end_date

    # add processor Id
    conf['general']['processor_id'] = str(index)
    conf['general']['clear_netcdf_cache'] = 'false'

    return conf

def write_rose_conf(result_dir, conf_filename, 
                    template_conf, rose_conf, model, diag, index, 
                    start_date, end_date):
    """
    Write the configuration file

    result_dir     : result directory
    conf_filename  : the original rose configuration file
    template_conf  : small template configuration
    rose_conf      : configuration object for conf_filename
    model          : model name
    diag           : diag name
    index          : 0...n
    start_date     : start date for this model (or '')
    end_date       : end date for this model (or '')
    """

    # create the configuration from the template
    conf = create_model_diag_conf(rose_conf, template_conf, 
                                  model, diag, index, start_date, end_date)

    # write the file
    fmt = '_{}'
    confilename = os.path.join(result_dir, conf_filename + fmt.format(index))
    with open(confilename, 'w') as configfile:
        conf.write(configfile)



def get_all_sections_of_type(rose_conf, pat):
    """
    Extract all the sections matching a given regex pattern

    rose_conf   : original rose configuration
    pat         : regex pattern  
    """
    res = ''
    for section in rose_conf.sections():
        m = re.match(pat, section)
        if m:
            res += ',' + m.group(1)

    return res[1:].split(',')


def main():

    rsn_config = Configparser()
    rsn.read('rosesnip.rc')

    parser = argparse.ArgumentParser(description='Prepare parallel rose config files.')
    parser.add_argument('-c', dest='conf_filename', default='rose-app-expanded.conf', 
                           help='serial rose config file, for instance "rose-app-expanded.conf"')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory')
    parser.add_argument('-y', dest='num_years', type=int, default=rsn_config['general']['num_years'], 
                              help='number of years in each processor group')
    parser.add_argument('-C', dest='clear', action='store_true', help='start by removing any files in output directory')
    args = parser.parse_args()

    # read the configuration file
    if not os.path.exists(args.conf_filename):
        raise FileNotFoundError('File {} does not exist!'.format(args.conf_filename))
    rose_conf = ConfigParser()
    rose_conf.read(args.conf_filename)

    models = get_all_sections_of_type(rose_conf, PAT_MODEL)
    diags = get_all_sections_of_type(rose_conf, PAT_DIAG)

    print('configuration file: {}'.format(args.conf_filename))
    print('models            : {}'.format(models))
    print('diags             : {}'.format(diags))
    print('{} models x {} diagnostics'.format(len(models), len(diags)))

    # prepare the result directory, choosing its name, creating it or
    # cleaning its content
    if not args.result_dir:
        # generate name for temporary directory
        dt =  datetime.now()
        args.result_dir = \
           'result_{:02}{:02}{:02}T{:02}h{:02}m{:02}s'.format(dt.year, dt.month, dt.day, 
                                                              dt.hour, dt.minute, dt.second)
    if args.result_dir[0] != '/':
        # add the full path
        args.result_dir = os.getcwd() + '/' + args.result_dir
    # create output directory if not present
    if not os.path.exists(args.result_dir):
        os.mkdir(args.result_dir)
    else:
        if args.clear:
            # remove all the files
            for f in os.listdir(args.result_dir):
                os.remove(f)
    print('saving results in dir: {}.'.format(args.result_dir))

    # copy the original rose config file and reset the output directory to point
    # to args.result_dir
    ori_conf = ConfigParser()
    ori_conf.read(args.conf_filename)
    ori_conf['general']['output_dir'] = args.result_dir
    with open(args.result_dir + '/' + os.path.basename(args.conf_filename), 'w') as f:
        ori_conf.write(f)

    # create a small template conf file without models or diags
    template_conf = generate_template_conf(rose_conf, result_dir=args.result_dir)

    # generate all the micro configuration files
    index = 0
    for diag in diags:

        diag_def = rose_conf['namelist:diags(' + diag + ')']
        if diag_def['enabled'] == 'false':
            # skip
            print('info: skipping disabled diag {}...'.format(diag))
            continue

        for model in models:

            model_def = rose_conf['namelist:models(' + model + ')']
            if model_def['enabled'] == 'false':
                # skip
                print('info: skipping disabled model {}...'.format(model))
                continue

            start_date = model_def.get('start_date', '')
            end_date = model_def.get('end_date', '')

            if not start_date or not end_date:

                # don't split in years

                sdt = '' or start_date
                edt = '' or end_date
                print('info: no year parallelization in model {}...'.format(model))
                write_rose_conf(args.result_dir, args.conf_filename, 
                                template_conf, rose_conf, model, diag, index, 
                                start_date=sdt, end_date=edt)
                index += 1

            else:

                # start/end dates are defined for this model

                split_dates = split_time_range(start_date, end_date, steps=args.num_years)

                # iterate over the time windows
                for i in range(len(split_dates) - 1):

                    sdt = split_dates[i]
                    edt = split_dates[i + 1]
                    write_rose_conf(args.result_dir, args.conf_filename, 
                                    template_conf, rose_conf, model, diag, index, 
                                    start_date=sdt, end_date=edt)
                    index += 1


if __name__ == '__main__':
    main()
