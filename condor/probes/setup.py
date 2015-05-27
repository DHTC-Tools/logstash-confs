#!/usr/bin/env python

# Copyright 2015 University of Chicago
# Available under Apache 2.0 License

from distutils.core import setup

setup(name='htcondor-es-probes',
      version='0.5',
      description='HTCondor probes for Elasticsearch analytics',
      author='Suchandra Thapa',
      author_email='sthapa@ci.uchicago.edu',
      url='https://github.com/DHTC-Tools/logstash-confs/tree/master/condor',
      packages=['probe_libs'],
      scripts=['collect_history_info.py', 'get_job_status.py'],
      data_files=[('/etc/init.d/', 'scripts/collect_history'),
                  ('/etc/cron.d/', 'config/schedd_probe'),
                  ('/etc/sysconfig', 'config/collect_history')]
     )
