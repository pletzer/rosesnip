import sys
import argparse
if sys.version_info.major >= 3:
    from configparser import ConfigParser
else:
    from ConfigParser import ConfigParser
import copy


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
        if not section != 'general' and \
               section != dname and \
               section != mname:
            # remove this section
            del conf[section]
    # set the start and send dates
    conf[mname]['start_date'] = start_date
    conf[mname]['end_date'] = end_date
    # add processor Id
    conf['general']['processor_id'] = str(index)

    return conf


def main():

    parser = argparse.ArgumentParser(description='Generate parallel rose config files.')
    parser.add_argument('--models', dest='models', default='u-bc179', 
                           help='specify comma separated list of models, for instance "u-bc179,u-bc292"')
    parser.add_argument('--diags', dest='diags', default='tas_global', 
                           help='specify comma separated list of diagnostics, for instance "tas_global,"')
    parser.add_argument('--configuration', dest='conf_filename', default='rose-app-expanded.conf', help='serial rose config file, for instance "rose-app-expanded.conf"')
    parser.add_argument('--num_procs', dest='num_procs', default=1, type=int, help='number of processors')
    parser.add_argument('--output_dir', dest='output_dir', default='./', help='output directory')
    args = parser.parse_args()

    print('configuration file: {}'.format(args.conf_filename))
    print('models            : {}'.format(args.models))
    print('diags             : {}'.format(args.diags))
    print('num processors    : {}'.format(args.num_procs))

    # run some checks
    if args.num_procs < 1:
        raise ValueError('ERROR: num processors {} < 1!'.format(args.num_procs))

    # read the configuration file
    rose_conf = read_config(args.conf_filename)

    index = 0
    for diag in diags:
        diag_def = conf['namelist:diags(' + diag + ')']
        for model in models:
            model_def = conf['namelist:models(' + model + ')']
            start_date = model_def['start_date']
            end_date = model_def['end_date']
            for sdt, edt in split_time_range(start_date, end_date, args.num_procs):
                conf = generate_conf(rose_conf, start_date, end_date, model, diag, index)
                # write the file
                with open(args.conf_filename + f'_{index}', 'w') as configfile:
                    conf.write(configfile)
                index += 1


if __name__ == '__main__':
    main()