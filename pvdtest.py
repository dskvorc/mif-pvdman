import atexit
import time
from pvdinfo import *
from pvdman import PvdManager


def printPvds():
    for pvdKey, pvd in pvdman.pvds.items():
      print pvd
    print ''


mtu = MTUInfo(1234)
route = RouteInfo(24, None, 600, '192.168.164.0')
rdnss = RDNSSInfo(600, ['192.168.164.2'])
dnssl = DNSSLInfo(600, ['zemris.fer.hr', 'fer.hr', 'fer.unizg.hr'])

prefix1 = PrefixInfo(24, True, True, 600, 600, '192.168.164.131')
prefix2 = PrefixInfo(24, True, True, 600, 600, '192.168.164.132')
prefix3 = PrefixInfo(24, True, True, 600, 600, '192.168.164.133')
prefix4 = PrefixInfo(24, True, True, 600, 600, '192.168.164.134')
prefix5 = PrefixInfo(24, True, True, 600, 600, '192.168.164.135')

pvdman = PvdManager()
#atexit.register(pvdman.cleanup)

pvd = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3e', mtu, [prefix1], [route], [rdnss], [dnssl], None, None)
pvdman.setPvd('eno16777736', pvd)
printPvds()
time.sleep(3)

pvd = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3e', mtu, [prefix1], [route], [rdnss], [dnssl], None, None)
pvdman.setPvd('eno16777736', pvd)
printPvds()
time.sleep(3)

pvd = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3e', mtu, [prefix1], [route], [rdnss], [dnssl], None, None)
pvdman.setPvd('eno16777736', pvd)
printPvds()
time.sleep(3)

pvd = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3e', mtu, [prefix2], [route], [rdnss], [dnssl], None, None)
pvdman.setPvd('eno16777736', pvd)
printPvds()
time.sleep(3)

pvd = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3e', mtu, [prefix2], [route], [rdnss], [dnssl], None, None)
pvdman.setPvd('eno16777736', pvd)
printPvds()
time.sleep(3)

pvd = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3e', mtu, [prefix3], [route], [rdnss], [dnssl], None, None)
pvdman.setPvd('eno16777736', pvd)
printPvds()
time.sleep(3)

pvd = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3a', mtu, [prefix1], [route], [rdnss], [dnssl], None, None)
pvdman.setPvd('eno16777736', pvd)
printPvds()
time.sleep(3)

pvd = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3b', mtu, [prefix1], [route], [rdnss], [dnssl], None, None)
pvdman.setPvd('eno16777736', pvd)
printPvds()
time.sleep(3)

pvd = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3c', mtu, [prefix1], [route], [rdnss], [dnssl], None, None)
pvdman.setPvd('eno16777736', pvd)
printPvds()


#print (pvdman.pvds)
#print (pvdman.listPvds())

#pvdman.removePvd('eno16777736', pvd1.pvdId)

#pvdman.ipdbNetns.serve_forever()

