PvD architecture overview / implementation details
===================================================
This document describes partial provisioning domain component (MIF-PvD)
implementation from: https://github.com/dskvorc/mif-pvdman

Overview
---------
MIF-PvD does not interfere with regular network behavior: all services and
settings network manager uses aren't changed. PvDs are implemented through
namespaces, thus only those newly created namespaces and their network settings
are managed by MIF-PvD. (MIF-PvD is orthogonal to existing system.)

MIF-PvD creates PvD for each received coherent PvD information set.
Currently only router advertisement messages (RAs) are used (1).
PvD is implemented by namespaces: each PvD has its own namespace with single
interface (besides loopback) of macvlan type, connected to physical interface
on which related PvD information came (where RA containing them arrived) (2).
Each created interface is assigned an IPv6 address (or more of them), as per
PvD information provided (3).

PvD aware client application uses pvd_api to get list of PvDs, and activate
chosen PvD. Dbus is used to connect to PvD service on localhost.
On PvD activation, client is switched to PvD's namespace and further network 
operation application performs are in that namespace (4).

Non-PvD aware clients operate as before. The can be forced to run within some
PvD by starting it with command: ip netns exec <pvd-name> <command with args>

(1) Modified PvD aware radvd service is used
    https://github.com/dskvorc/mif-radvd
(2) Possibility (maybe): if more PvDs should be combined for some reason,
    maybe more interfaces could be created and put in same namespace.
(3) Possibility (maybe/to be tested): maybe same IP address could be used in
    different PvDs (namespaces/interfaces) if they have different gateway
    (assuming kernel can forward received IP packet based on that).
(4) Problem: changing namespace requires root privileges. Until some solution
    is found, applications are run as root.


Implementation details (development/testing environment)
--------------------------------------------------------
Two virtual machines (Fedora 23, Ubuntu 14.04 tested) in VMware Player.

Services on router:
- radvd PvD aware NDP server:
  * https://github.com/dskvorc/mif-radvd
  * configurations from: https://github.com/dskvorc/mif-pvdman/tree/master/conf
- DNS server (optional, to be configured)
- web server (optional, for test case presentation)

Service on client - MIF-PvD:
- https://github.com/dskvorc/mif-pvdman
- start with sudo python3 main.py
  * (requires python3 + netaddr + pyroute2 modules)
  * (install python3-netaddr and python3-pyroute2 modules, or use pip3)
- NDP client (ndpclient.py):
  * send RS request (on startup)
  * listen for RAs
  * from RAs creates implicit and explicit pvd information,
    and send them to pvdman
- PvD Manager (pvdman.py):
  * keeps PvD data
  * creates PvDs: namespaces, interfaces
  * updates PvDs with new parameters
- dbus service (pvdserver.py):
  * responds to dbus requests from clients (applications on localhost)

Application API:
- https://github.com/dskvorc/mif-pvdman/client_api
- pvd_api - library with client side API
  * uses dbus to connect to PvD Manager
  * methods: pvd_get_by_id, pvd_activate
  * (requires glib2-devel package (libglib2-devel on fedora))
- API is used to select "current" PvD: all next network related operations
  will use that PvD (unless they were initialized before, in different PvD)
  until different PvD is selected
- test application client_api/example.c retrieves all PvDs from MIF-PvD, select
  PvD with Id given on command line, and executes given command in that PvD
  * usage: sudo ./example [pvd-id [some command with parameters]]
  * copy/paste pvd-id from printed list (when executed just as ./example)


Test case 1
------------
Simulate two routers and web server behind each. With two explicit PvD-s this
example demonstrates that from first PvD only first web server is reachable and
that from second PvD only second web server is reachable.

Simulated environment:
+-----------+              +-----------+          +-----------+
|           |              |           |          |           |
|           |              |           |          |    web    |
|  client   +--O----+---O--+   router  |--O----O--|   server  |
|           |       |      |     1     |          |     1     |
|           |       |      |           |          |           |
+-----------+       |      +-----------+          +-----------+
                    |
                    |      +-----------+          +-----------+
                    |      |           |          |           |
                    |      |           |          |    web    |
                    +---O--+   router  |--O----O--|   server  |
                           |     2     |          |     2     |
       Figure 1            |           |          |           |
                           +-----------+          +-----------+


Real test environment (2):

      O eth0                eth0 O
      |                          |
+-----+-----+              +-----+-----+  
|           |         eth1 |           |  
|           | eth1   +--O--+           |  
|  client   +--O-----+     |   router  |  
|           |        +--O--+           |  
|           |         eth2 |           |  
+-----------+              +-----------+
                Figure 2

Router settings:
-----------------
Addresses: (eth0 used for Internet access on both virtual machines)
router-eth1: local link + 2001:db8:1::1/64, 2001:db8:2::1/64
router-eth2: local link + 2001:db8:3::1/64, 2001:db8:4::1/64
radvd:
 - on eth1: prefix 2001:db8:1/64 (implicit PvD)
            prefix 2001:db8:2/64 (explicit PvD, inside PvD container)
 - on eth2: prefix 2001:db8:3/64 (implicit PvD)
            prefix 2001:db8:4/64 (explicit PvD, inside PvD container)

httpd.conf on router:
Listen [2001:db8:2::1]:80
Listen [2001:db8:4::1]:80
...
<VirtualHost [2001:db8:2::1]:80>
DocumentRoot "/var/www/html/www1" # index.html: Hello from WWW1
</VirtualHost>
<VirtualHost [2001:db8:4::1]:80>
DocumentRoot "/var/www/html/www2" # index.html: Hello from WWW2
</VirtualHost>
/var/www/html

Since httpd accepts connections made on wrong interface (e.g. when packet with
IP address of eth2 arrives on eth1), additional filtering is required to
simulate setup from Figure 1.
Added iptables rules on router:
sudo ip6tables -A INPUT -6 -i eth1 -d 2001:db8:3::1 -j DROP
sudo ip6tables -A INPUT -6 -i eth1 -d 2001:db8:4::1 -j DROP
sudo ip6tables -A INPUT -6 -i eth2 -d 2001:db8:1::1 -j DROP
sudo ip6tables -A INPUT -6 -i eth2 -d 2001:db8:2::1 -j DROP
(when packet arrive on wrong interface ignore it)

Client settings:
-----------------
Physical interfaces not managed by MIF-PvD
IP addresses on virtual devices set per PvD information by MIF-PvD.

All RAs arrive on eth1 => virtual devices (macvlan) created for namespaces are
bound to this interface (@if3 suffix on virtual interface).
Example "ip a":
$ sudo ./example 4176b877-e8be-8242-9540-6ea13a3a1d60 ip a
[cut]
4: mifpvd@if3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default 
    link/ether c2:fa:bb:bc:5c:49 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet6 2001:db8:1:0:c0fa:bbff:febc:5c49/64 scope global 
       valid_lft forever preferred_lft forever
    inet6 fe80::c0fa:bbff:febc:5c49/64 scope link 
       valid_lft forever preferred_lft forever

Test results
-------------
PvDs:
4176b877-e8be-8242-9540-6ea13a3a1d60 ns:mifpvd-3 iface:eth1 2001:db8:1:0:c0fa:bbff:febc:5c49
f037ea62-ee4f-44e4-825c-16f2f5cc9b3f ns:mifpvd-4 iface:eth1 2001:db8:2:0:dce8:1fff:fe21:8d4a
cf44e119-7e3f-e302-549b-82a9c6fd6210 ns:mifpvd-1 iface:eth1 2001:db8:3:0:2880:68ff:fe8d:add0
f037ea62-ee4f-44e4-825c-16f2f5cc9b3e ns:mifpvd-2 iface:eth1 2001:db8:4:0:38f5:32ff:fe4f:d50a

sudo ./example 4176b877-e8be-8242-9540-6ea13a3a1d60 wget http://[2001:db8:2::1]:80
OK (index.html saved: WWW1)
sudo ./example f037ea62-ee4f-44e4-825c-16f2f5cc9b3f wget http://[2001:db8:2::1]:80
OK (index.html saved: WWW1)
sudo ./example cf44e119-7e3f-e302-549b-82a9c6fd6210 wget http://[2001:db8:2::1]:80
FAIL (Connecting to [2001:db8:2::1]:80... ^C)
sudo ./example f037ea62-ee4f-44e4-825c-16f2f5cc9b3e wget http://[2001:db8:2::1]:80
FAIL (Connecting to [2001:db8:2::1]:80... ^C)

sudo ./example 4176b877-e8be-8242-9540-6ea13a3a1d60 wget http://[2001:db8:4::1]:80
FAIL (Connecting to [2001:db8:4::1]:80... ^C)
sudo ./example f037ea62-ee4f-44e4-825c-16f2f5cc9b3f wget http://[2001:db8:4::1]:80
FAIL (Connecting to [2001:db8:4::1]:80... ^C)
sudo ./example cf44e119-7e3f-e302-549b-82a9c6fd6210 wget http://[2001:db8:4::1]:80
OK (index.html saved: WWW2)
sudo ./example f037ea62-ee4f-44e4-825c-16f2f5cc9b3e wget http://[2001:db8:4::1]:80
OK (index.html saved: WWW2)

