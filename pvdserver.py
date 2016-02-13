import json, dbus, dbus.service
from pvdman import PvdManager

# TODO create introspection xml file and put it into
# $(datadir)/dbus-1/interfaces (probably /usr/share/dbus-1/interfaces)

# test pvd data
testpvds = [
	("pvd-id-wired-0", "default", "eth0", "" ),
	("pvd-id-wired-1", "test", "eth1", "" ),
	("pvd-id-loopback", "default", "lo", "" )
]
empty_pvd = ("", "", "", "")

class PvdApiServer ( dbus.service.Object ):
	''' TODO '''
	def __init__(self, pvdman=None):
		self.pvdman = pvdman
		# using system bus - put pvd-man.conf file into /etc/dbus-1/system.d/
		bus_name = dbus.service.BusName('org.freedesktop.PvDManager', bus=dbus.SystemBus())
		dbus.service.Object.__init__(self, bus_name, '/org/freedesktop/PvDManager')

	def __get_pvds (self):
		if self.pvdman:
			return self.pvdman.getPvds()
		else: #test only!
			return testpvds

	@staticmethod
	def __format_pvds_for_reply (pvds):
		if isinstance ( pvds, list ):
			ret = []
			for pvd in pvds:
				ret.append( (pvd[0], pvd[1], pvd[2], json.dumps(pvd[3]) ) )
			ret.sort ( key = lambda i:i[1])
		else:
			ret = ( pvds[0], pvds[1], pvds[2], json.dumps(pvds[3]) )
		return ret

	@dbus.service.method('org.freedesktop.PvDManager')
	def get_by_id ( self, pvd_id ):
		''' application request specific pvd information, or list of pvds '''
		pvds = self.__get_pvds ()

		if pvd_id != "*":
			p = [ pvd for pvd in pvds if str(pvd_id) in pvd[0] ]
		else: # return all pvds client is allowed for
			p = pvds
		if not p:
			p = [empty_pvd]
		return self.__format_pvds_for_reply (p)

	@dbus.service.method('org.freedesktop.PvDManager')
	def activate ( self, pvd_id, pid ):
		''' return pvd information for that specific pvd '''
		pvds = self.__get_pvds ()
		p = [ pvd for pvd in pvds if str(pvd_id) == pvd[0] ]
		if len(p) == 1:
			p = p[0]
		else:
			p = empty_pvd

		# TODO save pid with pvd/namespace

		return self.__format_pvds_for_reply (p)

	@dbus.service.signal('org.freedesktop.PvDManager')
	def stateChanged ( self, message ):
		# call it like self.stateChanged ( pvd_id ) # id of pvd which changed
		# TODO
		pass

	@dbus.service.method('org.freedesktop.PvDManager')
	def get_by_properties ( self, properties ):
		''' application request specific pvd information, or list of pvds '''
		# properties is a json string defining required properties
		props = json.loads(properties)
		pvds = self.__get_pvds ()

		# filter pvds: remove ones that don't satisfy criteria
		for pvd in pvds[:]:
			pvd_props = pvd[3]
			for prop in props:
				val = pvd_props.get(prop)
				# if not => use default values: TODO
				if pvd in pvds and ( not val or props[prop] not in val ):
					pvds.remove(pvd)

		# sort pvds by properties: TODO

		if not pvds:
			pvds = [empty_pvd]

		return self.__format_pvds_for_reply (pvds)


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
