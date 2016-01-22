import dbus
import dbus.service
from pvdman import PvdManager

# TODO create introspection xml file and put it into
# $(datadir)/dbus-1/interfaces (probably /usr/share/dbus-1/interfaces)

# test pvd data
testpvds = [
	{"id":"pvd-id-wired-0", "iface":"eth0", "policy":"" },
	{"id":"pvd-id-wired-1", "iface":"eth1", "policy":"" },
	{"id":"pvd-id-loopback", "iface":"lo", "policy":"" }
]

empty_pvd_list = [{"id":"", "iface":"", "policy":""}]

class PvdApiServer ( dbus.service.Object ):
	''' TODO '''
	def __init__(self, pvdman=None):
		self.pvdman = pvdman
		# using system bus - put pvd-man.conf file into /etc/dbus-1/system.d/
		bus_name = dbus.service.BusName('org.freedesktop.PvDManager', bus=dbus.SystemBus())
		dbus.service.Object.__init__(self, bus_name, '/org/freedesktop/PvDManager')

	def __get_pvds (self):
		if self.pvdman:
			x = self.pvdman.listPvds()
			pvds = [{"id":pvd[1], "iface":pvd[0], "policy":"" } for pvd in x ]
		else: #test only!
			pvds = testpvds
		return pvds

	def __return_pvds (self, pvds):
		if not pvds:
			pvds = empty_pvd_list
		ret = [ ( pvd["id"], pvd["iface"], pvd["policy"] ) for pvd in pvds ]
		return ret

	@dbus.service.method('org.freedesktop.PvDManager')
	def get_by_id ( self, pvd_id ):
		''' application request specific pvd information, or list of pvds '''
		pvds = self.__get_pvds()
		if pvd_id != "*":
			p = [ pvd for pvd in pvds if str(pvd_id) in pvd["id"] ]
		else: # return all pvds client is allowed for
			p = pvds
		return self.__return_pvds (p)

	@dbus.service.method('org.freedesktop.PvDManager')
	def get_by_policy ( self, policy ):
		''' application request specific pvd information, or list of pvds '''
		pvds = self.__get_pvds()
		if len(policy) > 0:
			p = [ pvd for pvd in pvds if str(policy) in pvd["policy"] ]
		else: # return all pvds client is allowed for
			p = pvds
		return self.__return_pvds (p)

	@dbus.service.method('org.freedesktop.PvDManager')
	def attach ( self, pvd_id, pid ):
		# application indicates it want to use specific pvd
		return True

	@dbus.service.method('org.freedesktop.PvDManager')
	def detach ( self, pvd_id, pid ):
		# application indicates it want to use specific pvd
		return True


# for test only! (included from main.py)
if __name__ == "__main__":
	import dbus.mainloop.glib
	from gi.repository import GObject

	# main loop, dbus initialization
	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	apiDBUSResponder = PvdApiServer()

	loop = GObject.MainLoop()
	print("PvdApiServer running")
	loop.run()
