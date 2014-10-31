#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
./process_logs.py --date $1 --save-raw
