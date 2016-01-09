import os
import shutil
from pvdinfo import *
from pyroute2 import netns
from pyroute2 import IPRoute
from pyroute2 import IPDB

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
  # TODO: remove this, just for testing in IPv4-only environment
  __DEF_GATEWAY = '192.168.77.2'

  __NETNS_PREFIX = 'mifpvd-'
  __netnsIdGenerator = 0;
  __PVD_IFACE_PREFIX = 'mifpvd-'
  __pvdIfaceIdGenerator = 0;
  __DNS_CONF_FILE = '/etc/netns/%NETNS_NAME%/resolv.conf'
  
  
  def __init__(self):
    self.pvds = {}
    self.ipRoot = IPRoute()
    self.ipdbRoot = IPDB()
    self.ipdbRoot.register_callback(self.__onIfaceStateChange)
    self.ipNetns = None
    self.ipdbNetns = None


  def __onIfaceStateChange(self, ipdb, msg, action):
    if (ipdb == self.ipdbRoot):
      netnsName = 'root'
    elif (ipdb == self.ipdbNetns):
      netnsName = 'netns'

    if (action == 'RTM_NEWLINK' or action == 'RTM_DELLINK'):
      for attr in msg['attrs']:
        if attr[0] == 'IFLA_IFNAME':
          ifaceName = attr[1]
        elif attr[0] == 'IFLA_OPERSTATE':
          ifaceState = attr[1]
      if (action == 'RTM_NEWLINK'):
        print netnsName + ': ' + ifaceName + ' ADDED, state: ' + ifaceState
      elif (action == 'RTM_DELLINK'):
        print netnsName + ': ' + ifaceName + ' DELETED, state: ' + ifaceState


  def __getNetnsName(self):
    netnsName = None
    while (not netnsName or netnsName in netns.listnetns()):
      self.__netnsIdGenerator += 1;
      netnsName = self.__NETNS_PREFIX + str(self.__netnsIdGenerator)
    return netnsName
    
    
  def __getPvdIfaceName(self):
    pvdIfaceName = None
    while (not pvdIfaceName or len(self.ipRoot.link_lookup(ifname=pvdIfaceName)) > 0):
      self.__pvdIfaceIdGenerator += 1;
      pvdIfaceName = self.__PVD_IFACE_PREFIX + str(self.__pvdIfaceIdGenerator)
    return pvdIfaceName


  def __getDnsConfPath(self, netnsName):
    dnsConfFile = self.__DNS_CONF_FILE.replace('%NETNS_NAME%', netnsName)
    dnsConfDir = dnsConfFile[0:dnsConfFile.rfind('/')]
    return (dnsConfDir, dnsConfFile)


  def setPvd(self, phyIfaceName, pvdInfo):
    phyIfaceIndex = self.ipRoot.link_lookup(ifname=phyIfaceName)
    if (len(phyIfaceIndex) > 0):
      phyIfaceIndex = phyIfaceIndex[0]
      if (self.pvds.get((phyIfaceName, pvdInfo.pvdId)) is None):
        # create a record to track the configured PvDs
        pvd = PvdRecord(pvdInfo.pvdId, pvdInfo, phyIfaceName, self.__getPvdIfaceName(), self.__getNetnsName())

        # create a new network namespace to isolate the PvD configuration
        # the namespace with the given name should not exist, according to the name selection procedure specified in __getNetnsName()
        netns.create(pvd.netnsName)

        # create a virtual interface where PvD parameters are going to be configured, then move the interface to an isolated network namespace
        self.ipRoot.link_create(ifname=pvd.pvdIfaceName, kind='macvlan', link=phyIfaceIndex)
        pvdIfaceIndex = self.ipRoot.link_lookup(ifname=pvd.pvdIfaceName)
        self.ipRoot.link('set', index=pvdIfaceIndex[0], net_ns_fd=pvd.netnsName)
        
        # change the namespace and get a new NETLINK handles to operate in new namespace
        netns.setns(pvd.netnsName)
        self.ipNetns = IPRoute()
        self.ipdbNetns = IPDB()
        self.ipdbNetns.register_callback(self.__onIfaceStateChange)

        # get new index since interface has been moved to a different namespace
        loIfaceIndex = self.ipNetns.link_lookup(ifname='lo')
        if (len(loIfaceIndex) > 0):
          loIfaceIndex = loIfaceIndex[0]
        pvdIfaceIndex = self.ipNetns.link_lookup(ifname=pvd.pvdIfaceName)
        if (len(pvdIfaceIndex) > 0):
          pvdIfaceIndex = pvdIfaceIndex[0]

        # start interfaces
        self.ipNetns.link_up(loIfaceIndex)
        self.ipNetns.link_up(pvdIfaceIndex)

        # clear interface configuration if exists
        self.ipNetns.flush_addr(index=pvdIfaceIndex)
        self.ipNetns.flush_routes(index=pvdIfaceIndex)
        self.ipNetns.flush_rules(index=pvdIfaceIndex)

        # configure the interface with data received in RA message
        if (pvdInfo.mtu):
          self.ipNetns.link('set', index=pvdIfaceIndex, mtu=pvdInfo.mtu.mtu)

        if (pvdInfo.prefixes):
          for prefix in pvdInfo.prefixes:
            self.ipNetns.addr('add', index=pvdIfaceIndex, address=prefix.prefix, prefixlen=prefix.prefixLength)

        if (pvdInfo.routes):
          for route in pvdInfo.routes:
            # TODO: some IPV4 routes are added during interface prefix configuration, skip them if already there
            try:
              self.ipNetns.route('add', dst=route.prefix, mask=prefix.prefixLength, oif=pvdIfaceIndex, rtproto='RTPROT_STATIC', rtscope='RT_SCOPE_LINK')
            except:
              pass
        # TODO: default route for IPv4
        self.ipNetns.route('add', dst='0.0.0.0', oif=pvdIfaceIndex, gateway=self.__DEF_GATEWAY, rtproto='RTPROT_STATIC')

        # configure DNS data in resolv.conf
        if (pvdInfo.rdnsses or pvdInfo.dnssls):
          (dnsConfDir, dnsConfFile) = self.__getDnsConfPath(pvd.netnsName)
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
        self.pvds[(phyIfaceName, pvd.pvdId)] = pvd
      else:
        raise Exception('PvD duplicate error: PvD with ID ' + pvdInfo.pvdId + ' is already configured on ' + phyIfaceName + '.')
    else:
      raise Exception('Interface ' + phyIfaceName + ' does not exist.')


  def removePvd(self, phyIfaceName, pvdId):
    pvd = self.pvds.get((phyIfaceName, pvdId))
    if (pvd):
      if (pvd.netnsName in netns.listnetns()):
        netns.remove(pvd.netnsName)
      (dnsConfDir, dnsConfFile) = self.__getDnsConfPath(pvd.netnsName)
      if (os.path.exists(dnsConfDir)):
        shutil.rmtree(dnsConfDir, True)
      del self.pvds[(phyIfaceName, pvdId)]
    else:
      raise Exception('There is no PvD with ID ' + pvdInfo.pvdId + ' configured on ' + phyIfaceName + '.')
    

  def listPvds(self):
    pvdData = []
    for pvdKey, pvd in self.pvds.items():
      pvdData.append((pvd.phyIfaceName, pvd.pvdId))
    return pvdData


  def getPvdInfo(self, phyIfaceName, pvdId):
    return self.pvds.get((phyIfaceName, pvdId))


  def cleanup(self):
    for pvdKey, pvd in self.pvds.items():
      self.removePvd(pvd.phyIfaceName, pvd.pvdId)
