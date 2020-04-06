import sys
import argparse
import os
import subprocess
import re
import pandas

"""
Check status of submitted jobs
"""

completed_pat = re.compile(r'COMPLETED')

def main():

    parser = argparse.ArgumentParser(description='Check rose snip jobs.')
    parser.add_argument('-d', dest='result_dir', default='', help='specify result directory')
    args = parser.parse_args()

    csvfile = 'status.csv'
    csvfile = os.path.join(args.result_dir, csvfile)


    for job_id in df.loc[df.status == 'allocated', 'job_id']:
        cmd = 'sacct -j {}'.format(job_id)
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        if re.search(completed_pat, out):
            df.loc[df.job_id == job_id, 'status'] = 'completed'

    df = pandas.read_csv(csvfile)
    for st in 'UNKOWN', 'queued', 'allocated', 'completed':
        n = len(df.loc[df.status == 'UNKNOW'].index)
        print('Number of {} jobs: {}'.format(st, n))
 

if __name__ == '__main__':
    main()