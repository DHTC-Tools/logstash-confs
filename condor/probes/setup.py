#!/usr/bin/env python

# Copyright 2015 University of Chicago
# Available under Apache 2.0 License

from distutils.core import setup

setup(name='htcondor-es-probes',
      version='0.6.3',
      description='HTCondor probes for Elasticsearch analytics',
      author='Suchandra Thapa',
      author_email='sthapa@ci.uchicago.edu',
      url='https://github.com/DHTC-Tools/logstash-confs/tree/master/condor',
      packages=['probe_libs'],
      scripts=['collect_history_info.py', 'get_job_status.py'],
      data_files=[('/etc/init.d/', ['scripts/collect_history']),
                  ('/etc/cron.d/', ['config/schedd_probe']),
                  ('/var/lib/collect_history', []),
                  ('/etc/sysconfig', ['config/collect_history'])],
      license='Apache 2.0'
     )
