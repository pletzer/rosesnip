import sys
import argparse
import os
import subprocess
import re
import pandas

"""
Cancel submitted jobs
"""

completed_pat = re.compile(r'COMPLETED')

def main():

    parser = argparse.ArgumentParser(description='Cancel rose snip jobs.')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory')
    args = parser.parse_args()

    csvfile = 'status.csv'
    csvfile = os.path.join(args.result_dir, csvfile)


    try:
        df = pandas.read_csv(csvfile)
    except:
        # something bad happened
        print('ERROR: Could not read {}. Maybe you forgot to submit the jobs (rsn_submit)?'.format(csvfile))
        sys.exit(1)

    count = 0
    for st in 'queued', 'allocated':
        for job_id in df.loc[df.status == st, 'job_id']:
            cmd = 'scancel {}'.format(job_id)
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            df.loc[(df.status == st) & (df.job_id == job_id), 'status'] = 'cancelled'
            count += 1

    print('Killed {} jobs.'.format(count))
    df.to_csv(csvfile)
 

if __name__ == '__main__':
    main()