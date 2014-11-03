#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
./download_logs.py --date $1 --source $2
./process_logs.py --date $1 --save-raw
