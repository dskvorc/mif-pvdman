Test case 01
============

Network:
--------

+--------+                       +------+                                +------+
|        |      2001:db8:1::1/48 |      | 2001:db8:10::1  2001:db8:10::2 |      |
| Client +-o-+-----------------o-+  R1  |-o----------------------------o-|  S1  |
|        |   |                   |      |                                |      |
+--------+   |                   +------+                                +------+
             |
             |                   +------+                                +------+
             |  2001:db8:2::1/48 |      | 2001:db8:20::1  2001:db8:20::2 |      |
             +-----------------o-+  R2  |-o----------------------------o-|  S2  |
  Figure 1                       |      |                                |      |
                                 +------+                                +------+

PvDs:
-----
R1-PVD1: 2001:db8:1:1::/64 (implicit) { "type": ["internet", "wired"],    "bandwidth":"10 Mbps", "pricing":"free" }
R1-PVD2: 2001:db8:1:2::/64 (explicit) { "type": ["iptv", "wired"],        "bandwidth":"10 Mbps", "pricing":"free" }
R2-PVD1: 2001:db8:2:1::/64 (implicit) { "type": ["internet", "cellular"], "bandwidth":"1 Mbps",  "pricing":"0,01 $/MB" }
R2-PVD2: 2001:db8:2:2::/64 (explicit) { "type": ["voice", "cellular"],    "bandwidth":"1 Mbps",  "pricing":"0,01 $/MB" }


Testing:
--------
On each node, from conf/tc01/ run:
$ sudo ./run start <node-name>
For example, on router R1:
$ sudo ./run start R1

For stopping services:
$ sudo ./run stop <node-name>

For cleaning log files, added configuration files, temporary files:
$ sudo ./run clean <node-name>

On client node, after "sudo ./run start C", applications can be started from client_api/tests:
(from git root)
$ cd client_api/tests
$ make
$ ./pvd_list
$ sudo ./pvd_run <pvd-id> command


Example executions on client side, after all routers and servers were started:
------------------------------------------------------------------------------

List available PvDs
+++++++++++++++++++

$ ./pvd_list
Requesting all (*):
id: c79b1614-66bf-e259-82b0-807aaed34c17 ns:mifpvd-1 iface:eno33554984
properties: {"bandwidth": "1 Mbps", "type": ["internet", "cellular"], "name": "Cellular internet access", "id": "implicit", "pricing": "0,01 $/MB"}

id: f037ea62-ee4f-44e4-825c-16f2f5cc9b3e ns:mifpvd-2 iface:eno33554984
properties: {"bandwidth": "0,1 Mbps", "type": ["voice", "cellular"], "name": "Phone", "id": "f037ea62-ee4f-44e4-825c-16f2f5cc9b3e", "pricing": "0,01 $/MB"}

id: cfe25073-4d60-6f0b-d88f-1003c82a1817 ns:mifpvd-3 iface:eno33554984
properties: {"bandwidth": "10 Mbps", "type": ["internet", "wired"], "name": "Home internet access", "id": "implicit", "pricing": "free"}

id: f037ea62-ee4f-44e4-825c-16f2f5cc9b3f ns:mifpvd-4 iface:eno33554984
properties: {"bandwidth": "10 Mbps", "type": ["iptv", "wired"], "name": "TV", "id": "f037ea62-ee4f-44e4-825c-16f2f5cc9b3f", "pricing": "free"}

----
Order of pvds are determined by order of RAs MIF component received first.
In previous case, first to arrive were RAs of router R2 (not R1).
Therefore, mifpvd-1 and mifpvd-2 are provided by R2, others by R1.
----


Running commands in PvD given by PvD-Id
++++++++++++++++++++++++++++++++++++++
Lets try to reach S1 and S2 from mifpvd-1 (c79b1614-66bf-e259-82b0-807aaed34c17)

----
$ sudo ./pvd_run c79b1614-66bf-e259-82b0-807aaed34c17 wget http://[2001:db8:10::2]/pvd-test.html
Activating pvd: c79b1614-66bf-e259-82b0-807aaed34c17:
pvd c79b1614-66bf-e259-82b0-807aaed34c17 activated!
Executing: wget http://[2001:db8:10::2]/pvd-test.html
--2016-02-12 00:02:40--  http://[2001:db8:10::2]/pvd-test.html
Connecting to [2001:db8:10::2]:80... failed: Network is unreachable.

$ sudo ./pvd_run c79b1614-66bf-e259-82b0-807aaed34c17 wget http://[2001:db8:20::2]/pvd-test.html
Activating pvd: c79b1614-66bf-e259-82b0-807aaed34c17:
pvd c79b1614-66bf-e259-82b0-807aaed34c17 activated!
Executing: wget http://[2001:db8:20::2]/pvd-test.html
--2016-02-12 00:03:19--  http://[2001:db8:20::2]/pvd-test.html
Connecting to [2001:db8:20::2]:80... connected.
HTTP request sent, awaiting response... 200 OK
Length: 17 [text/html]
Saving to: ‘pvd-test.html’

pvd-test.html  100%[=====================================>] 17  --.-KB/s in 0s

2016-02-12 00:03:19 (2,53 MB/s) - ‘pvd-test.html’ saved [17/17]

$ cat pvd-test.html
Web server on S2
----

S2 is reachable over mifpvd-1 and mifpvd-2, S1 over mifpvd-3 and mifpvd-4.
----

Running commands in PvD given by properties
++++++++++++++++++++++++++++++++++++++++++

$ sudo ./pvd_prop_run "{\"type\":\"internet\",\"pricing\":\"free\"}" firefox http://[2001:db8:10::2]/swtrailer.mp4


Choose command depending on available PvDs
++++++++++++++++++++++++++++++++++++++++++

$ sudo ./pvd_fallback_example.sh

Script tries first to use PvD which has both "internet" and "free" properties.
If such PvD is available an example movie is streamed from S1.
If such PvD isn't available an example audio file is streamed from S2.

To demonstrate this feature, first stop services on R1, restart services on
client, and then run previous script. It should play audio.
Then start services on R1, and wait for its RAs to reach client (or restart
services on Client). Now it should stream video.


Using two PvDs simultaneously from single application
+++++++++++++++++++++++++++++++++++++++++++++++++++++

First, start echo_server on S1 and S2 (it should start automatically with run.sh).

$ sudo ./multi_pvd_echo_client \
  cfe25073-4d60-6f0b-d88f-1003c82a1817 2001:db8:10::2 20000 \
  c79b1614-66bf-e259-82b0-807aaed34c17 2001:db8:20::2 20000
12121212

Client opens two sockets, each in its PvD:
- 1st one will go to S1 through R1 (since R1 is default gateway for 1st PVD)
- 2nd one will go to S2 through R2 (since R2 is default gateway for 2nd PVD)

Output "121212..." its echo from S1 (1's) and S2 (2's).
