#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
./process_logs.py $1 save
