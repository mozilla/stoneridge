#!/bin/bash
#
# stoneridge_master	Stone Ridge master setup
# 
# chkconfig: 2345 98 09
# description: stoneridge_master is responsible for serving builds and \
#              uploading results to the graph server

### BEGIN INIT INFO
# Provides: stoneridge master
# Required-Start: $local_fs $network
# Required-Stop: $local_fs $network
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start and stop stoneridge master
# Description: stoneridge serves builds and uploads results
### END INIT INFO

### BEGIN CONFIGURATION SECTION
SRHOME=/home/hurley/srhome
### END CONFIGURATION SECTION

CONFFILE=$SRHOME/stoneridge.ini

start() {
}

stop() {
}

case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart|force-reload|reload)
    stop
    start
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|reload|force-reload}"
    exit 2
esac
