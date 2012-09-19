#!/bin/bash
#
# stoneridge_server	Stone Ridge server setup
# 
# chkconfig: 2345 98 09
# description: stoneridge_server is responsible for serving resources and \
#              maintaining network conditions
# processname: httpd
# pidfile: 
# config: /home/hurley/srhome/conf/httpd.conf

### BEGIN INIT INFO
# Provides: stoneridge server
# Required-Start: $local_fs $network
# Required-Stop: $local_fs $network
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start and stop stoneridge server
# Description: stoneridge server sets network conditions and serves resources
### END INIT INFO

### BEGIN CONFIGURATION SECTION
SRHOME=/home/hurley/srhome
MAINIP=172.17.0.1
RATE=10mbit
MAXBURST=10240
LIMIT=30720
LATENCY=90ms
JITTER=
CORRELATION=
### END CONFIGURATION SECTION

PIDFILE=$SRHOME/srnamed.pid
LOGFILE=$SRHOME/srnamed.log

start() {
    # Setup eth1 to have an address
    ip addr add $MAINIP/12 dev eth1
    # Setup our network conditions on eth1
    tc qdisc add dev eth1 root handle 1:0 tbf rate $RATE maxburst $MAXBURST limit $LIMIT
    tc qdisc add dev eth1 parent 1:1 handle 10:0 netem latency $LATENCY $JITTER $CORRELATION
    # Start srnamed
    python $SRHOME/stoneridge/srrun.py $SRHOME/stoneridge/srnamed.py --listen $MAINIP --pidfile $PIDFILE --log $LOGFILE
    # Start apache
    $SRHOME/bin/apachectl start
}

stop() {
    # Stop apache
    $SRHOME/bin/apachectl stop
    # Stop srnamed
    kill $(cat $PIDFILE)
    # Remove network conditions
    tc qdisc del dev eth1 root
    # Remove ip addresses from eth1
    ip addr del $MAINIP/12 dev eth1
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
