# MIF PvD Manager

Prior to run mif-pvdman, following Python modules need to be installed: netaddr, pyroute2.
Install them using the following commands:

  $ sudo pip install --upgrade netaddr
  $ sudo pip install --upgrade pyroute2

To register mif-pvdman with D-Bus, copy conf/pvd-man.conf to /etc/dbus-1/system.d/

  $ sudo cp conf/pvd-man.conf /etc/dbus-1/system.d/

Run the mif-pvdman using:

  $ sudo python3 main.py
