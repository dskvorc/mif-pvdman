import atexit
from pvdinfo import *
from pvdman import PvdManager

mtu = MTUInfo(1234)
prefix = PrefixInfo(24, True, True, 600, 600, '192.168.77.130')
route = RouteInfo(24, None, 600, '192.168.77.0')
rdnss = RDNSSInfo(600, ['192.168.77.2'])
dnssl = DNSSLInfo(600, ['zemris.fer.hr', 'fer.hr', 'fer.unizg.hr'])
pvd1 = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3e', mtu, [prefix], [route], [rdnss], [dnssl], None, None)
pvd2 = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3f', mtu, [prefix], [route], [rdnss], [dnssl], None, None)

pvdman = PvdManager()
atexit.register(pvdman.cleanup)

pvdman.setPvd('eno16777736', pvd1)
pvdman.setPvd('eno16777736', pvd2)

print (pvdman.pvds)
print (pvdman.listPvds())

#pvdman.removePvd('eno16777736', pvd1.pvdId)

#pvdman.ipdbNetns.serve_forever()

