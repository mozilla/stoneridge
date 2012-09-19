#!/bin/bash
#
# stoneridge_client	Stone Ridge client setup
# 
# chkconfig: 2345 98 09
# description: stoneridge_client is responsible for running tests

### BEGIN INIT INFO
# Provides: stoneridge client
# Required-Start: $local_fs $network
# Required-Stop: $local_fs $network
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start and stop stoneridge client
# Description: stoneridge client runs tests
### END INIT INFO

### BEGIN CONFIGURATION SECTION
SRHOME=/home/hurley/srhome
MYIP=172.16.1.1
### END CONFIGURATION SECTION

PIDFILE=$SRHOME/srdns.pid
LOGFILE=$SRHOME/srdns.log

start() {
    ip addr add $MYIP/12 dev eth1
    python $SRHOME/stoneridge/srrun.py $SRHOME/stoneridge/srdns.py --pidfile $PIDFILE --log $LOGFILE
}

stop() {
    kill $(cat $PIDFILE)
    ip addr del $MYIP/12 dev eth1
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
