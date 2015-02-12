Scripts to handle processing log files and loading it into elasticsearch
automatically.  

process_daily_dcache_log.sh needs to be run on faxbox so that it can 
copy the files to the appropriate location

load_elasticsearch_dcache_daily.sh should be run after process_daily_dcache_log.sh 
is completed (give it few hours to be safe)
