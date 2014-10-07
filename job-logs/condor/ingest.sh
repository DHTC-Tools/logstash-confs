#!/bin/bash

./process_logs.py
 /opt/logstash/bin/logstash -f joblog.conf
