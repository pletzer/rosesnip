import sys
import argparse
if sys.version_info.major >= 3:
    from configparser import ConfigParser
else:
    from ConfigParser import ConfigParser
import os
import re
from datetime import datetime
import copy

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

    returns a list [(start_date0, end_date0), (start_date1, end_date1), ....]
    """
    res = []
    sdt = start_date
    start_year = get_year(start_date)
    end_year = get_year(end_date)
    for y in range(start_year, end_year, steps):

        s = str(y) + '-01-01'
        if y == start_year:
            s = start_date

        e = str(y +1) + '-01-01'
        if y == end_year:
            e = end_date

        res.append((s, e))

    return res


def generate_template_conf(rose_conf):
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
    return conf 


def create_model_diag_conf(rose_conf, templ_conf, start_date, end_date, model, diag, index):
    """
    Add model and diag sections to configuration

    rose_conf   : original rose configuration
    templ_conf  : template configuration, will be copied
    start_date  : start date to add to model section
    end_date    : end date to add to model section
    model       : model name
    diag        : diag name
    index       : processor id

    returns a configuration
    """

    conf = copy.copy(templ_conf)

    mname = 'namelist:models(' + model + ')'
    dname = 'namelist:diags(' + diag + ')'
    conf[mname] = rose_conf[mname]
    conf[dname] = rose_conf[dname]
    # set the start and send dates
    conf[mname]['start_date'] = start_date
    conf[mname]['end_date'] = end_date
    # add processor Id
    conf['general']['processor_id'] = str(index)

    return conf


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

    parser = argparse.ArgumentParser(description='Prepare parallel rose config files.')
    parser.add_argument('-c', dest='conf_filename', default='rose-app-expanded.conf', 
                           help='serial rose config file, for instance "rose-app-expanded.conf"')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory')
    parser.add_argument('-y', dest='num_years', type=int, default=10, help='number of years in each processor group')
    parser.add_argument('-C', dest='clear', action='store_true', help='start by removing any files in output directory')
    args = parser.parse_args()

    # read the configuration file
    rose_conf = ConfigParser()
    rose_conf.read(args.conf_filename)
    rose_conf = read_config(args.conf_filename)

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
        args.result_dir = 'result_{}-{:02}-{02}-{:02}_{:02}_{:02}_{:02}'.format(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        print(f'saving results in dir: {args.result_dir}')
    # create output directory if not present
    if not os.path.exists(args.result_dir):
        os.mkdir(args.result_dir)
    else:
        if args.clear:
            # remove all the files
            for f in os.listdir(args.result_dir):
                os.remove(f)

    template_conf = generate_template_conf(rose_conf)

    # generate all the micro configuration files
    index = 0
    for diag in diags:
        diag_def = rose_conf['namelist:diags(' + diag + ')']
        for model in models:
            model_def = rose_conf['namelist:models(' + model + ')']
            start_date = model_def['start_date']
            end_date = model_def['end_date']
            # iterate over the time windowss
            for sdt, edt in split_time_range(start_date, end_date, steps=args.num_years):
                conf = create_model_diag_conf(rose_conf, template_conf, 
                                           start_date, end_date, model, diag, index)
                # write the file
                confilename = os.path.join(args.result_dir, args.conf_filename + f'_{index}')
                with open(confilename, 'w') as configfile:
                    conf.write(configfile)
                index += 1


if __name__ == '__main__':
    main()