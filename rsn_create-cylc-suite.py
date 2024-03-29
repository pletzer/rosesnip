import sys
import argparse
import os
import glob
import re
from configparser import ConfigParser

"""
Generate a cylc workflow
"""

WORKFLOW_RC_TEMPLATE = \
"""
[meta]
    title = "Submit parallel monitor jobs"

[scheduler]

[task parameters]
        procid = 0..{max_index}

[scheduling]
   [[queues]]
       [[[default]]]
           # max number of concurrent jobs
           limit = {max_num_concurrent_jobs}   
   [[dependencies]]
        R1 = "run<procid> => final_run"

[runtime]
    {batch}
    [[run<procid>]]
        script = "sh {result_dir}/rsn_run.sh ${{CYLC_TASK_PARAM_procid}}"
    [[final_run]] 
        script = "sh {result_dir}/rsn_run.sh"
"""

SLURM_TEMPLATE = \
"""
    [[root]]
            platform = maui-ancil-slurm
            execution time limit = {exec_time_limit}
        [[[directives]]]
            --account={account}
            --partition={partition}
            --export=NONE
            --tasks=1
            --cpus-per-task=1
"""

RUN_TEMPLATE = """#!/usr/bin/bash 
# This file is autogenerated, do not edit

export SCITOOLS_MODULE=none
export PYTHON_EXEC={python_exec}
set +u # ignore undefined variables, takes care of a tput error

if [ $# == 0 ]
then
    # final run, create plots, etc. from cached data
    mkdir -p {result_dir}/nc
    cp -r {result_dir}/[0-9][0-9][0-9][0-9][0-9]/nc/* {result_dir}/nc
    {abrun_exec} {app_name} -c {result_dir}/{conf_file_base} -v
else
    index=$(printf "%05d" $1)
    {abrun_exec} {app_name} -c {result_dir}/$index/{conf_file_base} -v
fi

set -u # restore 
"""


def gather_in_directory(result_dir):

    directories = [d for d in os.listdir(result_dir) if re.match(r'\d+', d)]
    if len(directories) == 0:
        print('Warning: could not find any [0-9]+ directories under {}'.format(result_dir))
        return '', 0
    conf_file_base = os.path.basename( glob.glob(result_dir + '/' + directories[0] + '/*.conf')[0] )
    max_index = len(directories) - 1

    return conf_file_base, max_index

def main():

    rsn_config = ConfigParser()
    rsn_config.read('rosesnip.rc')

    parser = argparse.ArgumentParser(description='Generate CYLC flow.cylc file.')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory (output of rsn_prepare.py)')
    parser.add_argument('-a', dest='abrun_exec', default=rsn_config['afterburner']['abrun_exec'], 
                              help='full path to abrun.sh executable')
    parser.add_argument('-A', dest='app_name', default=rsn_config['afterburner']['app_name'],
                              help='name of afterburner app')
    parser.add_argument('-m', dest='max_num_concurrent_jobs', default=rsn_config['general']['max_num_concurrent_jobs'], 
                              help='max number of concurrent jobs')
    parser.add_argument('-I', dest='interactive', action='store_true', help='create flow.cylc file for for interactive execution (default is SLURM)')
    parser.add_argument('-p', dest='python_exec', default=rsn_config['afterburner']['python_exec'], 
                              help='path to python executable')
    parser.add_argument('-L', dest='exec_time_limit', default=rsn_config['general']['exec_time_limit'], 
                            help='execution time limit for each task')
    parser.add_argument('--account', dest='account', default=rsn_config['slurm']['account'], 
                            help='SLURM account number')
    parser.add_argument('--partition', dest='partition', default=rsn_config['slurm']['partition'], 
                            help='SLURM partition')
    args = parser.parse_args()

    # make sure we dealing with full paths
    if args.result_dir[0] != '/':
        args.result_dir = os.getcwd() + '/' + args.result_dir

    if args.abrun_exec[0] != '/':
        args.abrun_exec = os.getcwd() + '/' + args.abrun_exec

    # run a few checks
    if not os.path.exists(args.result_dir):
        print('ERROR: result dir {} does not exist'.format(args.result_dir))
        sys.exit(1)

    if not os.path.exists(args.abrun_exec):
        print('ERROR: {} does not exist'.format(args.abrun_exec))
        sys.exit(2)

    conf_file_base, max_index = gather_in_directory(args.result_dir)

    # parameters
    params = {
        'max_index': max_index,
        'max_num_concurrent_jobs': args.max_num_concurrent_jobs,
        'exec_time_limit': args.exec_time_limit,
        'abrun_exec': args.abrun_exec,
        'python_exec': args.python_exec,
        'app_name': args.app_name,
        'conf_file_base': conf_file_base,
        'batch': '',
        'pwd': os.getcwd(),
        'result_dir': args.result_dir,
        'account': args.account,
        'partition': args.partition,
        }
    if not args.interactive:
        params['batch'] = SLURM_TEMPLATE.format(**params)

    # create run script
    run_filename = '{result_dir}/rsn_run.sh'.format(**params)
    with open(run_filename, 'w') as f:
        f.write(RUN_TEMPLATE.format(**params))
    print('Run script is {}.'.format(run_filename))

    # create flow.cylc
    workflow_filename = '{result_dir}/flow.cylc'.format(**params)
    with open(workflow_filename, 'w') as f:
        f.write(WORKFLOW_RC_TEMPLATE.format(**params))
    print('Cylc workflow file is {}.'.format(workflow_filename))

if __name__ == '__main__':
    main()
