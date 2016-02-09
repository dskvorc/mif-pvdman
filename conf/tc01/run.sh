#!/bin/sh

# Update values here!

# assuming: DEV0 - general internet access - not to be used during test
#           DEV1, DEV2 - for tests, have assigned link-local IPv6 addresses
DEV0=eno16777736 # device that should be turned off during tests
DEV1=eno33554984 # first device used in tests
DEV2=eno50332208 # second device usen in tests (empty if not used)

MIFDIR=../.. #root directory of PVD-MAN (with conf/tcXX subdir where configuration files are)
TCDIR=. #directory where test case files are (e.g. $MIFDIR/conf/tc01)

HTTPDDIR=/etc/apache2/sites-enabled #where to store info for web server
HTTPDPROG=apache2
# it is assumed that standard httpd is already configured and serving from
# directory: /var/www/html

# IP addresses for routers and servers (client will get them via MIF manager)
R1_IP6_1=2001:db8:1::1/64
R1_IP6_2=2001:db8:1::2/64
R2_IP6_1=2001:db8:2::1/64
R2_IP6_2=2001:db8:2::2/64
S1_IP6_1=2001:db8:10::1/64
S2_IP6_1=2001:db8:20::1/64


Usage () {
  echo "Usage: $0 start|stop C|R1|R2|S1|S2"
  exit
}
if [ "$1" != "start" -a "$1" != "stop" ]; then Usage; fi
if [ "$2" != "C" -a "$2" != "R1" -a "$2" != "R2" -a "$2" != "S1" -a "$2" != "S2" ]; then Usage; fi

eval IP1=\$${2}_IP6_1
eval IP2=\$${2}_IP6_2

if [ "$1" = "start" ]; then
  # disable other connections (NetworkManager)
  if [ -n "$DEV0" ]; then nmcli device disconnect $DEV0; fi
  
  if [ "$2" = "C" ]; then
    # C - client specific code
    python3 $MIFDIR/main.php -i $DEV1 > pvd-man.log &
    echo "mif-pvd man started"
    echo "start pvd-aware programs now"
  else
    # R1/R2/S1/S2
    sysctl -w net.ipv6.conf.all.forwarding=1
    if [ -z "$IP1" ]; then
      echo "Address for DEV1 must be provided for $2"
      exit
    fi
    /sbin/ip -6 addr add $IP1 dev $DEV1

    if [ "$2" = "R1" -o "$2" = "R2" ]; then
      if [ -z "$IP2" ]; then
        echo "Address for DEV2 must be provided for $2"
        exit
      fi
      /sbin/ip -6 addr add $IP2 dev $DEV2
      sed s/IFACE/$DEV1/ < $TCDIR/$2/radvd.conf > radvd.conf
      /usr/local/sbin/radvd -d 5 -n -C radvd.conf -m logfile -l radvd.log &
      echo "radvd started"
    fi
    # http
    systemctl stop $HTTPDPROG.service
    LLA=`ip addr show dev $DEV1 scope link | grep inet6 | cut -c 11- | cut -d / -f 1`
    sed s/LLAIFACE/$LLA\%$DEV1/ < $TCDIR/$2/httpd.conf > $HTTPDDIR/pvd-httpd.conf
    mkdir -p /var/www/html/pvdinfo
    cp -f $TCDIR/$2/pvd-info.json /var/www/html/pvdinfo/
    echo "WWW-1" > /var/www/html/pvd-test.html
    systemctl start $HTTPDPROG.service
  fi

else # stop

  # enable other connections
  if [ -n "$DEV0" ]; then nmcli device connect $DEV0; fi
  
  if [ "$2" = "C" ]; then
    killall python3 && echo "mif-pvd man stopped"
  else
    # R1/R2/S1/S2
    sysctl -w net.ipv6.conf.all.forwarding=0
    if [ -n "$IP1" ]; then /sbin/ip -6 addr del $IP1 dev $DEV1; fi
    if [ "$2" = "R1" -o "$2" = "R2" ]; then
      if [ -n "$IP2" ]; then /sbin/ip -6 addr del $IP2 dev $DEV2; fi
      killall radvd && echo "radvd stopped"
      rm -f radvd.conf
    fi
    # http
    systemctl stop $HTTPDPROG.service
    rm -f $HTTPDDIR/pvd-httpd.conf
    rm -rf /var/www/html/pvdinfo/
    rm -f /var/www/html/pvd-test.html
  fi
fi

