import sys
import argparse
import os
import glob
import subprocess
import re
from datetime import datetime

"""
Submit the previously generated rose-configuration files
"""

queued_pat = re.compile(r'job (\d+) queued')
allocated_pat = re.compile(r'job (\d+) has been allocated')


def get_job_id(output):

    # convert byte to string (required by Python3)
    output = output.decode("utf-8")

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
    parser.add_argument('-T', dest='test', action='store_true', help='test only, do not submit jobs')
    args = parser.parse_args()

    csvfile = 'status.csv'
    csv = open(os.path.join(args.result_dir, csvfile), 'w')
    csv.write('rose_conf_filename,job_id,status,submission_date,submission_time\n')

    for conffile in glob.glob(args.result_dir + '/*.conf_[0-9]*'):
        slurm_options = '--output={}/slurm-%a.out --time={} --mem={}'.format(args.result_dir, args.time, args.mem)

        # build the command
        cmd = 'srun {} {} {} -c {} -v'.format(slurm_options, args.abrun, args.monitorModel, conffile)
        if args.test:
            # testing only
            cmd = 'echo ' + cmd
            print(cmd)

        # execute the command
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

        # get the job_id and status of the job
        job_id, stat = get_job_id(out)

        # store
        dt = datetime.now()
        now_date = '{}-{:02}-{:02}'.format(dt.year, dt.month, dt.day)
        now_time = '{:02}:{:02}:{:02}'.format(dt.hour, dt.minute, dt.second)
        csv.write('{},{},{},{},{}\n'.format(conffile, job_id, stat, now_date, now_time))

    csv.close()


if __name__ == '__main__':
    main()