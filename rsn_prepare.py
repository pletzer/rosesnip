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
from configparser import ConfigParser

"""
Prepare micro rose configuration files for parallel processing
"""

# regex pattern for diag sections
PAT_DIAG = re.compile(r'namelist:diags\(([^\)]+)\)')
# regex pattern for model sections
PAT_MODEL = re.compile(r'namelist:models\(([^\)]+)\)')



def generate_template_conf(rose_conf, result_dir):
    """
    Returns a template configuration without models or diags

    rose_conf  : original rose configuration
    result_dir : top result directory
    index      : processor id

    returns template configuration
    """
    conf = ConfigParser()
    for section in rose_conf.sections():
        if not re.match(PAT_MODEL, section) and not re.match(PAT_DIAG, section):
            # not a model and not a diag section so add
            conf[section] = rose_conf[section]

    return conf 


def create_model_diag_conf(rose_conf, templ_conf, model, diag, index):
    """
    Add model and diag sections to configuration

    rose_conf   : original rose configuration
    templ_conf  : template configuration, will be copied
    model       : model name
    diag        : diag name
    index       : processor id

    returns a configuration
    """

    conf = copy.deepcopy(templ_conf)

    mname = 'namelist:models(' + model + ')'
    dname = 'namelist:diags(' + diag + ')'
    conf[mname] = rose_conf[mname]
    conf[dname] = rose_conf[dname]

    conf['general']['clear_netcdf_cache'] = 'false'

    return conf

def write_rose_conf(result_dir, conf_filename, 
                    template_conf, rose_conf, model, diag, index):
    """
    Write the configuration file

    result_dir     : result directory
    conf_filename  : the original rose configuration file
    template_conf  : small template configuration
    rose_conf      : configuration object for conf_filename
    model          : model name
    diag           : diag name
    index          : 0...n
    """

    # create the configuration from the template
    conf = create_model_diag_conf(rose_conf, template_conf, 
                                  model, diag, index)

    # set the result_dir
    output_dir = result_dir + f'/{index:05}'
    conf['general']['output_dir'] = result_dir

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    # write the file
    confilename = os.path.join(output_dir, conf_filename)
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

    rsn_config = ConfigParser()
    rsn_config.read('rosesnip.rc')

    parser = argparse.ArgumentParser(description='Prepare parallel rose config files.')
    parser.add_argument('-c', dest='conf_filename', default='', 
                           help='serial rose config file, for instance "rose-app-expanded.conf"')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory')
    args = parser.parse_args()

    if not args.conf_filename:
        raise RuntimeError('ERROR: must specify rose config file (-c option)!')

    # read the configuration file
    if not os.path.exists(args.conf_filename):
        raise FileNotFoundError('ERROR: file {} does not exist!'.format(args.conf_filename))
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
        raise RuntimeError('ERROR: must specify result directory (-d option)!')

    if args.result_dir[0] != '/':
        # add the full path
        args.result_dir = os.getcwd() + '/' + args.result_dir

    # create output directory if not present
    if not os.path.exists(args.result_dir):
        os.mkdir(args.result_dir)
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

    disabled_diags = set()
    disabled_models = set()

    # generate all the micro configuration files
    index = 0
    for diag in diags:

        diag_def = rose_conf['namelist:diags(' + diag + ')']
        if diag_def['enabled'] == 'false':
            # skip
            disabled_diags.add(diag)
            continue

        for model in models:

            model_def = rose_conf['namelist:models(' + model + ')']
            if model_def['enabled'] == 'false':
                # skip
                disabled_models.add(model)
                continue

            write_rose_conf(args.result_dir, args.conf_filename, 
                                template_conf, rose_conf, model, diag, index)
            index += 1

    print('disabled diags: {}'.format(disabled_diags))
    print('disabled models: {}'.format(disabled_models))


if __name__ == '__main__':
    main()
