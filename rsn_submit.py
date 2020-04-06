import sys
import argparse
import os
import glob
import subprocess
import re

"""
Submit the previously generated rose-configuration files
"""

queued_pat = re.compile('job (\d+) queued')
allocated_pat = re.compile('job (\d+) has been allocated')


def get_job_id(output):
    stat = 'UNKNOWN'
    job_id = -1

    m = re.search(queued_pat, output)
    if m:
        stat = 'queued'
        job_id = m.group(1)

    m = re.search(allocated_pat, output)
    if m:
        stat = 'allocated'
        job_id = m.group(1)

    return job_id, stat

def main():

    parser = argparse.ArgumentParser(description='Submit rose snip jobs.')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory')
    parser.add_argument('-M', dest='monitorModel', default='ModelMonitor3', help='specify name of app monitor')
    parser.add_argument('-t', dest='time', default='00:30:00', help='max time for submission jobs')
    parser.add_argument('-m', dest='mem', default='1g', help='max memory footprint of submission jobs')
    parser.add_argument('-a', dest='abrun', default='./turbofan/trunk/bin/abrun.sh', help='path to abrun.sh')
    args = parser.parse_args()

    csvfile = 'status.csv'
    csv = open(csvfile, 'w')
    csv.write('rose_conf_filename,job_id,status\n')

    for conffile in glob.glob(os.path.join(args.result_dir, '*.conf_[0-9]+'):
        cmd = 'echo srun --time={args.time} --mem={args.mem} {args.abrun} {args.monitorModel} -c {conffile} -v'
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        jobid, stat = get_job_id(out)
        csv.write('{},{},{}\n'.format(conffile, job_id, stat))

    csv.close()


if __name__ == '__main__':
    main()