import os
import shutil
import atexit
from pvdinfo import *
from pyroute2 import netns
from pyroute2 import IPRoute

class PvdRecord:
  def __init__(self, pvdId, pvdInfo, phyIfaceName, pvdIfaceName, netnsName):
    self.pvdId = pvdId
    self.pvdInfo = pvdInfo
    self.phyIfaceName = phyIfaceName
    self.pvdIfaceName = pvdIfaceName
    self.netnsName = netnsName


  def __repr__(self):
    return '(' + self.pvdId + ', ' + self.phyIfaceName + ', ' + self.pvdIfaceName + ', ' + self.netnsName + ')'

    
class PvdManager:
  pvds = {}

  __NETNS_PREFIX = 'mifpvd-'
  __netnsIdGenerator = 0;
  __PVD_IFACE_PREFIX = 'mifpvd-'
  __pvdIfaceIdGenerator = 0;
  __DNS_CONF_FILE = '/etc/netns/%NETNS_NAME%/resolv.conf'

  global ipRoot, ipNetns  
  ipRoot = IPRoute()


  @staticmethod
  def __getNetnsName():
    PvdManager.__netnsIdGenerator += 1;
    netnsName = PvdManager.__NETNS_PREFIX + str(PvdManager.__netnsIdGenerator)
    while (netnsName in netns.listnetns()):
      PvdManager.__netnsIdGenerator += 1;
      netnsName = PvdManager.__NETNS_PREFIX + str(PvdManager.__netnsIdGenerator)
    return netnsName
    
    
  @staticmethod
  def __getPvdIfaceName():
    PvdManager.__pvdIfaceIdGenerator += 1;
    pvdIfaceName = PvdManager.__PVD_IFACE_PREFIX + str(PvdManager.__pvdIfaceIdGenerator)
    while (len(ipRoot.link_lookup(ifname=pvdIfaceName)) > 0):
      PvdManager.__pvdIfaceIdGenerator += 1;
      pvdIfaceName = PvdManager.__PVD_IFACE_PREFIX + str(PvdManager.__pvdIfaceIdGenerator)
    return pvdIfaceName


  @staticmethod
  def __getDnsConfPath(netnsName):
    dnsConfFile = PvdManager.__DNS_CONF_FILE.replace('%NETNS_NAME%', netnsName)
    dnsConfDir = dnsConfFile[0:dnsConfFile.rfind('/')]
    return (dnsConfDir, dnsConfFile)


  @staticmethod
  def setPvd(phyIfaceName, pvdInfo):
    phyIfaceIndex = ipRoot.link_lookup(ifname=phyIfaceName)
    if (len(phyIfaceIndex) > 0):
      phyIfaceIndex = phyIfaceIndex[0]
      if (PvdManager.pvds.get((phyIfaceName, pvdInfo.pvdId)) is None):
        # create a record to track the configured PvDs
        pvd = PvdRecord(pvdInfo.pvdId, pvdInfo, phyIfaceName, PvdManager.__getPvdIfaceName(), PvdManager.__getNetnsName())

        # create a new network namespace to isolate the PvD configuration
        # the namespace with the given name should not exist, according to the name selection procedure specified in __getNetnsName()
        netns.create(pvd.netnsName)

        # create a virtual interface where PvD parameters are going to be configured, then move the interface to an isolated network namespace
        ipRoot.link_create(ifname=pvd.pvdIfaceName, kind='macvlan', link=phyIfaceIndex)
        pvdIfaceIndex = ipRoot.link_lookup(ifname=pvd.pvdIfaceName)
        ipRoot.link('set', index=pvdIfaceIndex[0], net_ns_fd=pvd.netnsName)
        
        # change the namespace and get a new IPRoute handle to operate in new namespace
        netns.setns(pvd.netnsName)
        ipNetns = IPRoute()

        # get new index since interface has been moved to a different namespace
        loIfaceIndex = ipNetns.link_lookup(ifname='lo')
        if (len(loIfaceIndex) > 0):
          loIfaceIndex = loIfaceIndex[0]
        pvdIfaceIndex = ipNetns.link_lookup(ifname=pvd.pvdIfaceName)
        if (len(pvdIfaceIndex) > 0):
          pvdIfaceIndex = pvdIfaceIndex[0]

        # start interfaces
        ipNetns.link_up(loIfaceIndex)
        ipNetns.link_up(pvdIfaceIndex)

        # clear interface configuration if exists
        ipNetns.flush_addr(index=pvdIfaceIndex)
        ipNetns.flush_routes(index=pvdIfaceIndex)
        ipNetns.flush_rules(index=pvdIfaceIndex)

        # configure the interface with data received in RA message
        if (pvdInfo.mtu):
          ipNetns.link('set', index=pvdIfaceIndex, mtu=pvdInfo.mtu.mtu)

        if (pvdInfo.prefixes):
          for prefix in pvdInfo.prefixes:
            ipNetns.addr('add', index=pvdIfaceIndex, address=prefix.prefix, prefixlen=prefix.prefixLength)

        if (pvdInfo.routes):
          for route in pvdInfo.routes:
            # TODO: some IPV4 routes are added during interface prefix configuration, skip them if already there
            try:
              ipNetns.route('add', dst=route.prefix, mask=prefix.prefixLength, oif=pvdIfaceIndex, rtproto='RTPROT_STATIC', rtscope='RT_SCOPE_LINK')
            except:
              pass
        # TODO: default route for IPv4
        ipNetns.route('add', dst='0.0.0.0', oif=pvdIfaceIndex, gateway=DEF_GATEWAY, rtproto='RTPROT_STATIC')

        # configure DNS data in resolv.conf
        if (pvdInfo.rdnsses or pvdInfo.dnssls):
          (dnsConfDir, dnsConfFile) = PvdManager.__getDnsConfPath(pvd.netnsName)
          # delete the namespace-related DNS configuration directory if exists and create empty one
          shutil.rmtree(dnsConfDir, True)
          os.makedirs(dnsConfDir)
          # create new resolv.conf file for a given namespace
          dnsConfFile = open(dnsConfFile, 'w')
          dnsConfFile.write('# Autogenerated by pvdman\n')
          dnsConfFile.write('# PvD ID: ' + pvdInfo.pvdId + '\n\n')

        if (pvdInfo.rdnsses):
          for rdnss in pvdInfo.rdnsses:
            if (rdnss.addresses):
              dnsConfFile.write('\n'.join('{} {}'.format('nameserver', address) for address in rdnss.addresses) + '\n\n')

        if (pvdInfo.dnssls):
          for dnssl in pvdInfo.dnssls:
            if (dnssl.domainNames):
              dnsConfFile.write('search ' + ' '.join('{}'.format(domainName) for domainName in dnssl.domainNames))

        # if PvD configuration completed successfully, add PvD record to the PvD manager's log
        PvdManager.pvds[(phyIfaceName, pvd.pvdId)] = pvd
      else:
        raise Exception('PvD duplicate error: PvD with ID ' + pvdInfo.pvdId + ' is already configured on ' + phyIfaceName + '.')
    else:
      raise Exception('Interface ' + phyIfaceName + ' does not exist.')


  @staticmethod
  def removePvd(phyIfaceName, pvdId):
    pvd = PvdManager.pvds.get((phyIfaceName, pvdId))
    if (pvd):
      if (pvd.netnsName in netns.listnetns()):
        netns.remove(pvd.netnsName)
      (dnsConfDir, dnsConfFile) = PvdManager.__getDnsConfPath(pvd.netnsName)
      if (os.path.exists(dnsConfDir)):
        shutil.rmtree(dnsConfDir, True)
      del PvdManager.pvds[(phyIfaceName, pvdId)]
    else:
      raise Exception('There is no PvD with ID ' + pvdInfo.pvdId + ' configured on ' + phyIfaceName + '.')
    

  @staticmethod
  def cleanup():
    for pvdKey, pvd in PvdManager.pvds.items():
      PvdManager.removePvd(pvd.phyIfaceName, pvd.pvdId)


#atexit.register(PvdManager.cleanup)

mtu = MTUInfo(1234)
prefix = PrefixInfo(24, True, True, 600, 600, '192.168.77.130')
route = RouteInfo(24, None, 600, '192.168.77.0')
DEF_GATEWAY = '192.168.77.2'
rdnss = RDNSSInfo(600, ['192.168.77.2'])
dnssl = DNSSLInfo(600, ['zemris.fer.hr', 'fer.hr', 'fer.unizg.hr'])
pvd1 = PvdInfo('f037ea62-ee4f-44e4-825c-16f2f5cc9b3f', mtu, [prefix], [route], [rdnss], [dnssl], None, None)
PvdManager.setPvd('eno16777736', pvd1)
print (PvdManager.pvds)

#PvdManager.removePvd('eno16777736', pvd1.pvdId)
