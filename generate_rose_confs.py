import sys
import argparse
if sys.version_info.major >= 3:
    from configparser import ConfigParser
else:
    from ConfigParser import ConfigParser
import copy
import time
import os
import re


"""
Generate rose configuration files for parallel processing
"""


def read_config(config_file=None):
    """
    Parse configuration options from a file in Rose's extended INI format
    and wrap it in an :class:`afterburner.app_config.AppConfig` object. Up
    :param str config_file: pathname of the configuration file to
        parse.
    """

    # If the config_file argument was not specified, check the --config-file
    # command-line argument

    # Still no luck? Raise an exception.
    if not config_file:
        raise AttributeError("No configuration file specified.")

    try:
        app_config = ConfigParser()
        app_config.read(config_file)
    except:
        raise ValueError(f"Error parsing configuration file {config_file}")

    return app_config

def get_year(dt):
    """Extract the year from YYYY-MM-DD*"""
    return int(dt.split('-')[0])

def get_month_day(dt):
    """Extract the month and day from YYYY-MM-DD-*"""
    return dt.split('-')[1:3]

def split_time_range(start_date, end_date, n):
    """
    Split a time range into n segments

    start_date : start date in YYYY-MM-DD format
    end_date   : end date in YYYY-MM-DD format

    returns a list [(start_date0, end_date0), (start_date1, end_date1), ....]
    """
    res = []
    sdt = start_date
    print(f'**** start_date = {start_date}')
    print(f'**** end_date = {end_date}')
    start_year = get_year(start_date)
    end_year = get_year(end_date)
    dy = (end_year - start_year)//n
    if dy == 0:
        raise ValueError("ERROR: either decrease -n or increase the end date's year")
    for i in range(1, n + 1):
        if i == n:
            edt = end_date
        else:
            edt = str(start_year  + i * dy) + '-01-01'   
        res.append((sdt, edt))
        sdt = edt
    return res

def generate_conf(rose_conf, start_date, end_date, model, diag, index):

    conf = copy.deepcopy(rose_conf)
    mname = 'namelist:models(' + model + ')'
    dname = 'namelist:diags(' + diag + ')'
    for section in conf.sections():
        if section != 'general' and \
               section != dname and \
               section != mname:
            # remove this section
            print(f'*** removing section >{section}<')
            del conf[section]
    # set the start and send dates
    conf[mname]['start_date'] = start_date
    conf[mname]['end_date'] = end_date
    # add processor Id
    conf['general']['processor_id'] = str(index)

    return conf

def get_all_diags(rose_conf):
    res = ''
    pat = re.compile(r'namelist:diags\(([^\)]+)\)')
    for section in rose_conf.sections():
        m = re.match(pat, section)
        if m:
            res += ',' + m.group(1)
    return res[1:]

def get_all_models(rose_conf):
    res = ''
    pat = re.compile(r'namelist:models\(([^\)]+)\)')
    for section in rose_conf.sections():
        m = re.match(pat, section)
        if m:
            res += ',' + m.group(1)
    return res[1:]


def main():

    parser = argparse.ArgumentParser(description='Generate parallel rose config files.')
    parser.add_argument('--models', dest='models', default='', 
                           help='specify comma separated list of models, for instance "u-bc179,u-bc292 (leave empty to include all models)"')
    parser.add_argument('--diags', dest='diags', default='', 
                           help='specify comma separated list of diagnostics, for instance "tas_global (leave empty to consider include diagnostics)"')
    parser.add_argument('--configuration', dest='conf_filename', default='rose-app-expanded.conf', help='serial rose config file, for instance "rose-app-expanded.conf"')
    parser.add_argument('--num_procs', dest='num_procs', default=1, type=int, help='number of processors')
    parser.add_argument('--output_dir', dest='output_dir', default='', help='specify output directory')
    parser.add_argument('--clear', dest='clear', action='store_true', help='start by removing files in output directory')
    args = parser.parse_args()

    # read the configuration file
    rose_conf = read_config(args.conf_filename)

    if not args.models:
        args.models = get_all_models(rose_conf)

    if not args.diags:
        args.diags = get_all_diags(rose_conf)

    print('configuration file: {}'.format(args.conf_filename))
    print('models            : {}'.format(args.models.split(',')))
    print('diags             : {}'.format(args.diags.split(',')))
    print('num processors    : {}'.format(args.num_procs))

    # run some checks
    if args.num_procs < 1:
        raise ValueError('ERROR: num processors {} < 1!'.format(args.num_procs))

    if not args.output_dir:
        # generate name for temporary directory
        args.output_dir = 'output_' + str(int(time.time() * 100))
        print(f'saving output in dir: {args.output_dir}')
    # create output directory if not present
    if not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)
    else:
        if args.clear:
            for f in os.listdir(args.output_dir):
                os.remove(f)

    index = 0
    for diag in args.diags.split(','):
        diag_def = rose_conf['namelist:diags(' + diag + ')']
        for model in args.models.split(','):
            model_def = rose_conf['namelist:models(' + model + ')']
            start_date = model_def['start_date']
            end_date = model_def['end_date']
            for sdt, edt in split_time_range(start_date, end_date, args.num_procs):
                conf = generate_conf(rose_conf, start_date, end_date, model, diag, index)
                # write the file
                confilename = os.path.join(args.output_dir, args.conf_filename + f'_{index}')
                with open(confilename, 'w') as configfile:
                    conf.write(configfile)
                index += 1


if __name__ == '__main__':
    main()