# rosesnip
A set of python scripts to automatically generate rose configuration files for parallel execution

## Overview

Postprocessing of climate data often involves computing averages and other statistical measures of diagnostic fields across models and for many simulation years. Afterburner is a Python application that performs these tasks. Currently, afterburner only runs on a single processor, which can make postprocessing slow. 

Roasesnip takes the same input as afterburner - a rose configuration file - and splits the job into many jobs that can run concurrently. The jobs are split across diagnostic fields, models and, if start and end dates are provided, across chunks of years. The reduction in turn around time can be significant, depending on the number of diagnostics, models and the number of years.


## Initial setup

Edit `rosesnip.rc` and enter the full path to the `abrun.sh` and `python` executables. Note that currently afterburner requires python 2. For example:

```
[afterburner]
    ...
    abrun_exec = /nesi/nobackup/nesi99999/pletzera/niwa00013/nesi/turbofan/pletzer/bin/abrun.sh
    python_exec = /opt/nesi/CS500_centos7_skl/Anaconda2/2019.10-GCC-7.1.0/bin/python
    ...
```


## How to use rosesnip

Running rosesnip involves three steps: (1) prepare the rose configureation files for parallel execution, (2) generate the cylc suit.rc file and (3) run the suite. 


### Prepare the rose configuration files

```
python rsn_prepare.py -d my_res_dir -c rose-app-expanded.conf
```

This will create directory `my_res_dir` and split file `rose-app-expanded.conf` into many small rose configureation files, each running a subset of tasks. 

### Generate the cylc suite file

```
python rsn_create-cylc-suite.py -d my_res_dir -s
```

Theis will create file `suite.rc`. Use option `-s` option to create SLURM jobs. 

### Submit the rosesnip job with cylc

Once `suite.rc` has been created, register the suite and submit the suite for execution:
```
cylc register rosesnip_1 /path/to/suite.rc
gcylc rosesnip_1 &
```

Upon completion, you will find netCDF files under `my_res_dir/nc` and plots under `my_res_dir/images`. It is also possible to create the plots interactively by executing

```
python rsn_plot.py -d my_res_dir -I
```





