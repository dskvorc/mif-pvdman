
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GObject
import socket
import argparse

from pvdman import PvdManager
from ndpclient import NDPClient
from pvdserver import PvdApiServer

def ndp_pending ( fd, cond, ndpc, pvdman ):
	''' Process received RAs '''
	pvdinfos = ndpc.get_pvdinfo()
	if pvdinfos:
		for ( iface, pvdInfo ) in pvdinfos:
			pvdman.setPvd ( iface, pvdInfo )

	return True

if __name__ == "__main__":
	# parse command line arguments
	parser = argparse.ArgumentParser()
	parser.add_argument ( '-i', required=False, type=str, help='interface name where to listen for RAs', dest='iface' )
	parser.add_argument ( '-u', required=False, type=str, help='PvD identifier to ask from radvd', dest='uuid' )
	arg = parser.parse_args()

	# create pvdmanager control object
	pvdman = PvdManager()
	print ( "PvdManager Initialized" )

	# main loop, dbus initialization
	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	apiDBUSResponder = PvdApiServer(pvdman)
	print ( "PvdApiServer Initialized" )

	# create ndpclient object and register socket for events
	ndpc = NDPClient( iface = arg.iface )
	sock = ndpc.get_sock ()
	GObject.io_add_watch ( sock.fileno(), GObject.IO_IN, ndp_pending, ndpc, pvdman )
	print ( "NDPClient Initialized" )
	# if interface was given, send RS over that interface (otherwise? sent to all interfaces?)
	if arg.iface:
		ndpc.send_rs ()

	# mail loop - wait for events
	loop = GObject.MainLoop()
	loop.run()
