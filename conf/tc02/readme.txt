
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

