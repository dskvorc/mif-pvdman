#!/bin/bash

Usage () {
  echo "Usage: $0 start|stop C|R1|R2|S1|S2"
  exit
}
if [ "$1" != "start" -a "$1" != "stop" ]; then Usage; fi
if [ "$2" != "C" -a "$2" != "R1" -a "$2" != "R2" -a "$2" != "S1" -a "$2" != "S2" ]; then Usage; fi

COMMAND=$1
ROLE=$2

function evaluate {
  input=$1
  output=$2
  echo -n "" > $output
  while read LINE; do
    eval X=\"$LINE\"
    echo $X >> $output
  done < $input
}

# assuming: DEV0 - general internet access - not to be used during test
#           DEV1, DEV2 - for tests, have assigned link-local IPv6 addresses

MIFDIR=../.. #root directory of PVD-MAN (with conf/tcXX subdir where configuration files are)
TCDIR=. #directory where test case files are (e.g. $MIFDIR/conf/tc01)
TMPDIR=__mif_cache__
HTTPDDIR=/etc/apache2/sites-enabled #where to store info for web server
HTTPDPROG=apache2
# it is assumed that standard httpd is already configured and serving from: /var/www/html

# get settings
source ./${ROLE}_conf.sh

if [ "$COMMAND" = "start" ]; then
  mkdir -p $TMPDIR
  # disable other connections (NetworkManager)
  if [ -n "$DEV0" ]; then nmcli device disconnect $DEV0; fi
  
  if [ "$ROLE" = "C" ]; then
    # C - client specific code
    python3 $MIFDIR/main.py -i $DEV1 2>$TMPDIR/pvdman-error.log 1> $TMPDIR/pvd-man.log &
    echo "mif-pvd man started"
    echo "start pvd-aware programs now"
  else
    # R1/R2/S1/S2
    sysctl -w net.ipv6.conf.all.forwarding=1
    if [ -z "$IP1" ]; then
      echo "Address for DEV1 must be provided for $ROLE"
      exit
    fi
    /sbin/ip -6 addr add $IP1 dev $DEV1

    if [ "$ROLE" = "R1" -o "$ROLE" = "R2" ]; then
      if [ -z "$IP2" ]; then
        echo "Address for DEV2 must be provided for $ROLE"
        exit
      fi
      /sbin/ip -6 addr add $IP2 dev $DEV2
      evaluate $TCDIR/radvd.conf $TMPDIR/radvd.conf
      /usr/local/sbin/radvd -d 5 -n -C $TMPDIR/radvd.conf -m logfile -l $TMPDIR/radvd.log &
      echo "radvd started"
    fi
    # http
    systemctl stop $HTTPDPROG.service
    sed s/NAME/$ROLE/ < $TCDIR/httpd.conf > $HTTPDDIR/pvd-httpd.conf
    mkdir -p /var/www/html/pvdinfo
    sed s/\"/\\\\\\\\\\\\\"/g < $TCDIR/pvd-info.json > $TMPDIR/pvd-info.json
    evaluate $TMPDIR/pvd-info.json /var/www/html/pvdinfo/pvd-info.json
    echo "Web server on $ROLE" > /var/www/html/pvd-test.html
    systemctl start $HTTPDPROG.service
  fi

else # stop

  # enable other connections
  if [ -n "$DEV0" ]; then nmcli device connect $DEV0; fi
  
  if [ "$ROLE" = "C" ]; then
    killall -SIGINT python3 && echo "mif-pvd man stopped"
  else
    # R1/R2/S1/S2
    sysctl -w net.ipv6.conf.all.forwarding=0
    if [ -n "$IP1" ]; then /sbin/ip -6 addr del $IP1 dev $DEV1; fi
    if [ "$ROLE" = "R1" -o "$ROLE" = "R2" ]; then
      if [ -n "$IP2" ]; then /sbin/ip -6 addr del $IP2 dev $DEV2; fi
      killall radvd && echo "radvd stopped"
    fi
    # http
    systemctl stop $HTTPDPROG.service
    rm -f $HTTPDDIR/pvd-httpd.conf
    rm -rf /var/www/html/pvdinfo/
    rm -f /var/www/html/pvd-test.html
  fi
fi

