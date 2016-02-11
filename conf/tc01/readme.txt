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
On particular node run:
$ sudo ./run start <node-name>
For example, on router R1:
$ sudo ./run start R1

For stopping services:
$ sudo ./run stop <node-name>

For cleaning log files, added configuration files, temporary files:
$ sudo ./run clean <node-name>

On client node, after "sudo ./run start C", applications can be started from client_api/tests:
(from git root)
$ cd client_api
$ make
$ cd tests
$ ./pvd_list
$ sudo ./pvd_run <pvd-id> command


Example execution (on client side, after all routers and servers were started):
-------------------------------------------------------------------------------
