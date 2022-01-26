#!/bin/sh
# cd ~/childlog/
/usr/bin/flock -w 0 /var/tmp/childlog.lock ./childlog_run.sh