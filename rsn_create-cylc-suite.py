import sys
import argparse
import os
import glob
import re

"""
Generate a cylc suite
"""

SUITE_RC_TEMPLATE = \
"""
[meta]
    title = "Submit parallel monitor jobs"

[cylc]
    [[parameters]]
        procid = 0..{max_index}

[scheduling]
   [[queues]]
       [[[default]]]
           # max number of concurrent jobs
           limit = {max_num_concurrent_jobs}   
   [[dependencies]]
        graph = run<procid> => stitch

[runtime]
    {batch}
    [[run<procid>]]
        script = '''
sh {pwd}/rsn_run.sh ${{CYLC_TASK_PARAM_procid}}
'''
    [[stitch]]
        script = "echo TO DO"
"""

SLURM_TEMPLATE = \
"""
    [[root]]
        [[[job]]]
            batch system = slurm
            execution time limit = PT1H
        [[[directives]]]
            --tasks=1
            --cpus-per-task=1
"""

RUN_TEMPLATE = \
"""
export TERM=xterm
export SCITOOLS_MODULE=none
module load module load Anaconda3/2020.02-GCC-7.1.0
module load PROJ
module load UDUNITS
{abrun_exec} {app_name} -c {conf_file_base}_${{1}} -v
module unload UDUNITS
module unload PROJ
module unload module load Anaconda3/2020.02-GCC-7.1.0
"""

def gather_in_directory(result_dir):

    files = glob.glob(result_dir + '/*.conf_[0-9]*')
    if len(files) == 0:
        print('Warning: could not find any *.conf_[0-9]* files under {}'.format(result_dir))
        return '', 0
    conf_file_base = re.sub('.conf_([0-9]*)', '.conf', files[0])
    max_index = len(files) - 1

    return conf_file_base, max_index

def main():

    parser = argparse.ArgumentParser(description='Generate CYLC suite.rc file.')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory (output of rsn_prepare.py)')
    parser.add_argument('-a', dest='abrun_exec', default='./abrun.sh', 
                              help='full path to abrun.sh executable')
    parser.add_argument('-A', dest='app_name', default='NetcdfModelMonitor', 
                              help='name of afterburner app')
    parser.add_argument('-m', dest='max_num_concurrent_jobs', default=2, 
                              help='max number of concurrent jobs')
    parser.add_argument('-s', dest='slurm', action='store_true', help='create suite.rc file for SLURM scheduler')
    args = parser.parse_args()

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
    d = {
        'max_index': max_index,
        'max_num_concurrent_jobs': args.max_num_concurrent_jobs,
        'abrun_exec': args.abrun_exec,
        'app_name': args.app_name,
        'conf_file_base': conf_file_base,
        'batch': '',
        'pwd': os.getcwd(),
        }
    if args.slurm:
        d['batch'] = SLURM_TEMPLATE

    # create run script
    with open('rsn_run.sh', 'w') as f:
        f.write(RUN_TEMPLATE.format(**d))

    # create suite.rc
    suite_name = 'suite.rc'
    with open(suite_name, 'w') as f:
        f.write(SUITE_RC_TEMPLATE.format(**d))
    
    print('Cylc suite written in file {}.'.format(suite_name))

if __name__ == '__main__':
    main()
