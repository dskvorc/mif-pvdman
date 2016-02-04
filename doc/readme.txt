PvD architecture overview / implementation details
===================================================
This document describes a proof-of-concept implementation of provisioning domain
(PvD) aware client-side network management component (MIF-pvdman). The source
code is available at https://github.com/dskvorc/mif-pvdman.

Contents
--------
1. Architecture Overview and Implementation Details
2. Description of Test Environment
3. Setup Instructions

1. Architecture Overview and Implementation Details
---------------------------------------------------
MIF-pvdman is a client-side component for IPv6 network auto-configuration based
on multiple provisioning domains (PvDs), as described in RFC 6418 and RFC 7556
(https://tools.ietf.org/html/rfc6418, https://tools.ietf.org/html/rfc7556).
MIF-pvdman is orthogonal to existing system, which means it does not interfere
with regular network behavior: none of the services and settings used by Network
Manager and similar components are not changed nor affected.

PvDs are implemented through Linux network namespaces. For each coherent PvD
information set received on the network interface, MIF-pvdman creates a separate
network namespace and configures received network parameters within that
namespace. Since each network namespace uses separate IP stack which is isolated
from other namespaces, potentially conflicting network parameters received from
different network providers can safely coexist on a single host. MIF-pvdman
manages only those newly created namespaces associated with the PvDs and their
network settings and leaves the default network namespace intact. That way, all
the existing network management components, such as Network Manager, continue to
work unobtrusively.

MIF-pvdman receives network configurations through Router Advertisement messages
(RAs). Modified version of PvD-aware radvd is used (1). Each RA may contain one
or more network configurations which are classified either as explicit or
implicit PvDs. Explicit PvD is a set of coherent NDP options explicitly labeled
with a unique PvD identifier and nested within a special NDP option called PVD
container, as described in draft-ietf-mif-mpvd-ndp-support-02
(https://tools.ietf.org/html/draft-ietf-mif-mpvd-ndp-support-02). Multiple
explicit PvDs may appear in a single RA, each within a different PvD container
option, as long as they are labeled with different PvD identifiers. Implicit PvD
is just another name for top-level NDP options placed outside the PvD container
option, as in regular non-PvD-aware router advertisements. Since implicit PvDs
are not labeled with PvD identifier, MIF-pvdman automatically generates an
identifier for internal use and configures the implicit PvD on the host in the
same way as if it was the explicit one. Only one implicit PvD is allowed per RA.
In current prototype, UUID is used as a PvD identifier.

Each PvD, either explicit or implicit, is associated with a network namespace
with a single virtual network interface (besides the loopback) of macvlan type,
where PvD-related network parameters are configured. To establish a connectivity
to the outside world, virtual interface is connected to the physical interface
on which the related PvD information is received through the RA (2). Each
virtual interface is assigned a link-local IPv6 address (fe80::/64) and one or
more addresses derived from Prefix Information options if present in the
received RA (3). Besides the IP addresses, MIF-pvdman configures the routing
tables and DNS records within the namespace. By default, a link-local and
default route via the RA-announcing router are added to the routing table,
regardless of the routing information received in RA. Additional routing
information is configured if Route Information options are received in RA.
Finally, for each RDNSS and DNSSL option received in RA, MIF-pvdman creates a
record in /etc/netns/NETNS_NAME/resolv.conf, where NETNS_NAME is a name of the
network namespace associated with the PvD.

PvD-aware client application uses PvD API to get a list of available PvDs
configured on the local host, and activate chosen PvD to use it for
communication. Information about configured PvDs are exposed to applications by
a special PvD service running on local host. D-Bus is used to connect
applications to PvD service. Upon PvD activation, client application is switched
to the network namespace associated with the selected PvD. Further network
operations (socket creation, sending and receiving data) are performed within
that namespace (4). Once obtained by the application, socket handles are linked
to the network namespace they were originally obtained from and continue to work
in that namespace, regardles of whether the application switches to another
namespace at some time later. This enables the application to use multiple PvDs
simultaneously. The only requirement is that the application is running within a
proper network namespace while obtaining a socket.

Non-PvD aware clients operate as before. Although they are not able to use PvD
API to select a certain PvD, they can still be forced to use a specific PvD by
starting them in a network namespace associated with that PvD. To run a program
within a given namespace, it should be started with:

    ip netns exec <pvd-namespace-name> <command with args>

(1) Modified PvD-aware radvd service is used
    https://github.com/dskvorc/mif-radvd
(2) Possibility for future extensions: if multiple PvDs should be grouped
    together for some reason, more virtual interfaces could be created per
    network namespace.
(3) Possibility (maybe/to be tested): maybe same IP address could be used in
    different PvDs (namespaces/interfaces) if they have different gateway
    (assuming kernel can forward received IP packet based on that).
(4) Problem: changing network namespace requires root privileges. Until more
    appropriate solution is found, applications are run as root.


2. Description of Test Environment
----------------------------------
Prototype system implementation described above is implemented and tested on
Linux/Fedora 23 and Linux/Ubuntu 14.04. Test environment consists of two
machines, one being a router running radvd, while another being a regular host
running MIF-pvdman and client applications. In our experiments, we used two
virtual machines hosted in VMware Player.

Services on router:
- radvd (PvD-aware NDP server):
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


Test Case
---------
Network environment consists of a client connected to two routers, each of them
having a web server behind. Web server 1 is only reachable through router 1,
while web server 2 is only reachable through router 2. Each router advertises
one PvD. Client receives network configuration from two PvDs and configures both
of them, but should carefully select the proper one to access a particular web
server.

Simulated environment:
+-----------+              +-----------+          +-----------+
|           |              |           |          |           |
|           |              |           |          |    web    |
|  client   +--o----+---o--+   router  |--o----o--|   server  |
|           |       |      |     1     |          |     1     |
|           |       |      |           |          |           |
+-----------+       |      +-----------+          +-----------+
                    |
                    |      +-----------+          +-----------+
                    |      |           |          |           |
                    |      |           |          |    web    |
                    +---o--+   router  |--o----o--|   server  |
                           |     2     |          |     2     |
       Figure 1            |           |          |           |
                           +-----------+          +-----------+


Real test environment:
Test environment consists of two virtual machines running on a single host. One
virtual machine behaves like a client, while another one simulates both routers
and web servers using separate network interfaces (router 1 + web server 1 on
eth1, router 2 + web server 2 on eth2).

      o eth0                  eth0 o
      |                            |
+-----+-----+              +-------+------+
|           |         eth1 |              |
|    VM1    | eth1   +--o--+     VM2      |
| (client)  +--o-----+     | (routers +   |
|           |        +--o--+ web servers) |
|           |         eth2 |              |
+-----------+              +--------------+
                Figure 2

Router settings:
----------------
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
----------------
Physical interfaces are not managed by MIF-pvdman.
IP addresses on virtual devices set per PvD information by MIF-pvdman.

All RAs arrive on eth1 => virtual devices (macvlan) created for namespaces are
bound to this interface (therefore @if3 suffix on virtual interface).
Example "ip a":
$ sudo ./pvd_run 4176b877-e8be-8242-9540-6ea13a3a1d60 ip a
[cut]
4: mifpvd@if3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default
    link/ether c2:fa:bb:bc:5c:49 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet6 2001:db8:1:0:c0fa:bbff:febc:5c49/64 scope global
       valid_lft forever preferred_lft forever
    inet6 fe80::c0fa:bbff:febc:5c49/64 scope link
       valid_lft forever preferred_lft forever

Test results
-------------
PvD configurations generated by MIF-pvdman:
PvD ID                                netns     iface  IP address
4176b877-e8be-8242-9540-6ea13a3a1d60  mifpvd-3  eth1   2001:db8:1:0:c0fa:bbff:febc:5c49
f037ea62-ee4f-44e4-825c-16f2f5cc9b3f  mifpvd-4  eth1   2001:db8:2:0:dce8:1fff:fe21:8d4a
cf44e119-7e3f-e302-549b-82a9c6fd6210  mifpvd-1  eth1   2001:db8:3:0:2880:68ff:fe8d:add0
f037ea62-ee4f-44e4-825c-16f2f5cc9b3e  mifpvd-2  eth1   2001:db8:4:0:38f5:32ff:fe4f:d50a

$ sudo ./pvd_run 4176b877-e8be-8242-9540-6ea13a3a1d60 wget http://[2001:db8:2::1]:80
OK (index.html saved: WWW1)
$ sudo ./pvd_run f037ea62-ee4f-44e4-825c-16f2f5cc9b3f wget http://[2001:db8:2::1]:80
OK (index.html saved: WWW1)
$ sudo ./pvd_run cf44e119-7e3f-e302-549b-82a9c6fd6210 wget http://[2001:db8:2::1]:80
FAIL (Connecting to [2001:db8:2::1]:80... ^C)
$ sudo ./pvd_run f037ea62-ee4f-44e4-825c-16f2f5cc9b3e wget http://[2001:db8:2::1]:80
FAIL (Connecting to [2001:db8:2::1]:80... ^C)

$ sudo ./pvd_run 4176b877-e8be-8242-9540-6ea13a3a1d60 wget http://[2001:db8:4::1]:80
FAIL (Connecting to [2001:db8:4::1]:80... ^C)
$ sudo ./pvd_run f037ea62-ee4f-44e4-825c-16f2f5cc9b3f wget http://[2001:db8:4::1]:80
FAIL (Connecting to [2001:db8:4::1]:80... ^C)
$ sudo ./pvd_run cf44e119-7e3f-e302-549b-82a9c6fd6210 wget http://[2001:db8:4::1]:80
OK (index.html saved: WWW2)
$ sudo ./pvd_run f037ea62-ee4f-44e4-825c-16f2f5cc9b3e wget http://[2001:db8:4::1]:80
OK (index.html saved: WWW2)