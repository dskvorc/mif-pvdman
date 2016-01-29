import os
import shutil
import time
import socket
import netaddr
import logging
import atexit
from pvdinfo import *
from pyroute2 import netns
from pyroute2 import IPRoute
from pyroute2 import IPDB

# initialize logger
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] [%(module)s] %(levelname)s: %(message)s')
LOG = logging.getLogger(__name__)


class Pvd:
  def __init__(self, pvdId, pvdInfo, phyIfaceName, pvdIfaceName, netnsName):
    self.pvdId = pvdId
    self.pvdInfo = pvdInfo
    self.phyIfaceName = phyIfaceName
    self.pvdIfaceName = pvdIfaceName
    self.netnsName = netnsName
    # timestamp when the PvD parameters were configured (we need this to calculate the expiration time of PvD parameters)
    self.__timestamp = int(time.time())

  def __repr__(self):
    return ('(' +
            self.pvdId + ', ' +
            self.phyIfaceName + ', ' +
            self.pvdIfaceName + ', ' +
            self.netnsName + ', ' +
            self.pvdInfo.prefixes[0].prefix + ', ' +
            str(self.__timestamp) +
            ')')

  def updateTimestamp(self):
    self.__timestamp = int(time.time())
    LOG.debug('timestamp updated for PvD {0}'.format(self.pvdId))


class PvdManager:
  __NETNS_PREFIX = 'mifpvd-'
  __netnsIdGenerator = 0;
  __PVD_IFACE_PREFIX = 'mifpvd-'
  __pvdIfaceIdGenerator = 0;
  __PVD_IFACE_TYPE = 'macvlan'

  __NETNSDIRNAME_REPLACE_PATTERN = '%NETNS_NAME%'
  __DNS_CONF_FILE = '/etc/netns/' + __NETNSDIRNAME_REPLACE_PATTERN + '/resolv.conf'

  __LOOPBACK_IFACE_NAME = 'lo'

  __NETNS_DEFAULT_PROC = '/proc/1/ns/net'
  __NETNS_DEFAULT_NAME = 'mifpvd-default'

  __DEFAULT_ROUTE_ADDRESS = '::'
  __LINK_LOCAL_PREFIX = 'fe80::'
  __LINK_LOCAL_PREFIX_LENGTH = 64


  '''
  PRIVATE METHODS
  '''

  def __init__(self):
    LOG.debug('PvdManager initialization started')
    self.pvds = {}
    self.ipRoot = IPRoute()
    self.ipdbRoot = IPDB()
    self.ipdbRoot.register_callback(self.__onIfaceStateChange)
    # create a symbolic link to be able to return to a default network namespace
    self.__createDefaultNetnsSymlink()
    # register a cleanup handler to remove configured PvDs and associated components at exit
    atexit.register(self.cleanup)
    LOG.debug('cleanup handler initialized')
    LOG.debug('PvdManager initialization finished')


  def __onIfaceStateChange(self, ipdb, msg, action):
    pass
    '''
    if (ipdb == self.ipdbRoot):
      netnsName = 'root'
    else:
      netnsName = 'netns'

    if (action == 'RTM_NEWLINK' or action == 'RTM_DELLINK'):
      for attr in msg['attrs']:
        if attr[0] == 'IFLA_IFNAME':
          ifaceName = attr[1]
        elif attr[0] == 'IFLA_OPERSTATE':
          ifaceState = attr[1]
      if (action == 'RTM_NEWLINK'):
        LOG.debug(netnsName + ': ' + ifaceName + ' ADDED, state: ' + ifaceState)
      elif (action == 'RTM_DELLINK'):
        LOG.debug(netnsName + ': ' + ifaceName + ' DELETED, state: ' + ifaceState)
    '''


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
    dnsConfFile = self.__DNS_CONF_FILE.replace(self.__NETNSDIRNAME_REPLACE_PATTERN, netnsName)
    dnsConfDir = dnsConfFile[0:dnsConfFile.rfind('/')]
    return (dnsConfDir, dnsConfFile)


  def __getDefaultNetnsSymlinkPath(self):
    netnsDir = netns.NETNS_RUN_DIR
    if (not netnsDir.endswith('/')):
      netnsDir += '/'
    return netnsDir + self.__NETNS_DEFAULT_NAME


  def __createDefaultNetnsSymlink(self):
    symlinkPath = self.__getDefaultNetnsSymlinkPath()
    if (not os.path.exists(os.path.dirname(symlinkPath))):
      os.makedirs(os.path.dirname(symlinkPath))
    if (os.path.exists(symlinkPath) and os.path.islink(symlinkPath)):
      os.unlink(symlinkPath)
    os.symlink(self.__NETNS_DEFAULT_PROC, symlinkPath)
    LOG.debug('symlink {0}->{1} created'.format(symlinkPath, os.readlink(symlinkPath)))


  def __removeDefaultNetnsSymlink(self):
    symlinkPath = self.__getDefaultNetnsSymlinkPath()
    if (os.path.exists(symlinkPath) and os.path.islink(symlinkPath)):
      # need to read the link target for logging prior to delete a link
      symlinkTarget = os.readlink(symlinkPath)
      os.unlink(symlinkPath)
    LOG.debug('symlink {0}->{1} removed'.format(symlinkPath, symlinkTarget))


  def __createNetns(self, phyIfaceIndex):
    netnsName = self.__getNetnsName()
    pvdIfaceName = self.__getPvdIfaceName()
    netns.create(netnsName)
    LOG.debug('network namespace {0} created'.format(netnsName))

    # create a virtual interface where PvD parameters are going to be configured, then move the interface to the new network namespace
    self.ipRoot.link_create(ifname=pvdIfaceName, kind=self.__PVD_IFACE_TYPE, link=phyIfaceIndex)
    LOG.debug('macvlan {0} created in default network namespace'.format(pvdIfaceName))
    pvdIfaceIndex = self.ipRoot.link_lookup(ifname=pvdIfaceName)
    self.ipRoot.link('set', index=pvdIfaceIndex[0], net_ns_fd=netnsName)
    LOG.debug('macvlan {0} moved to network namespace {1}'.format(pvdIfaceName, netnsName))

    # change the namespace and get new NETLINK handles to operate in new namespace
    netns.setns(netnsName)
    LOG.debug('network namespace switched to {0}'.format(netnsName))
    ip = IPRoute()
    ipdb = IPDB()
    ipdb.register_callback(self.__onIfaceStateChange)
    with open("/proc/sys/net/ipv6/conf/"+pvdIfaceName+"/accept_ra", 'w') as fp:
        fp.write("0")
    # return to a default network namespace to not cause a colision with other modules
    # ip and ipdb handles continue to work in the target network namespace
    netns.setns(self.__NETNS_DEFAULT_NAME)
    LOG.debug('network namespace switched to default')

    # get new index since interface has been moved to a different namespace
    loIfaceIndex = ip.link_lookup(ifname=self.__LOOPBACK_IFACE_NAME)
    if (len(loIfaceIndex) > 0):
      loIfaceIndex = loIfaceIndex[0]
    pvdIfaceIndex = ip.link_lookup(ifname=pvdIfaceName)
    if (len(pvdIfaceIndex) > 0):
      pvdIfaceIndex = pvdIfaceIndex[0]

    # start interfaces
    ip.link_up(loIfaceIndex)
    ip.link_up(pvdIfaceIndex)

    # clear network configuration if exists
    ip.flush_addr(index=pvdIfaceIndex)
    ip.flush_routes(index=pvdIfaceIndex)
    ip.flush_rules(index=pvdIfaceIndex)

    LOG.debug('macvlan {0} in network namespace {1} initialized'.format(pvdIfaceName, netnsName))

    return (netnsName, pvdIfaceName, ip)


  def __configureNetwork(self, ifaceName, pvdInfo, ip):
    if (pvdInfo):
      ifaceIndex = ip.link_lookup(ifname=ifaceName)
      if (len(ifaceIndex) > 0):
        ifaceIndex = ifaceIndex[0]

      # clear network configuration if exists
      ip.flush_addr(index=ifaceIndex)
      ip.flush_routes(index=ifaceIndex)
      ip.flush_rules(index=ifaceIndex)

      # set new network configuration
      if (pvdInfo.mtu):
        ip.link('set', index=ifaceIndex, mtu=pvdInfo.mtu.mtu)
        LOG.debug('MTU {0} on {1} configured'.format(pvdInfo.mtu.mtu, ifaceName))

      # get interface MAC address to derive the IPv6 address from
      iface = ip.get_links(ifaceIndex)[0]
      mac = iface.get_attr('IFLA_ADDRESS')

      # add link-local IPv6 address
      ipAddress = str(netaddr.EUI(mac).ipv6(netaddr.IPAddress(self.__LINK_LOCAL_PREFIX)))
      ip.addr('add', index=ifaceIndex, address=ipAddress, prefixlen=self.__LINK_LOCAL_PREFIX_LENGTH, rtproto='RTPROT_RA', family=socket.AF_INET6)
      LOG.debug('link-local IP address {0}/{1} on {2} configured'.format(ipAddress, self.__LINK_LOCAL_PREFIX_LENGTH, ifaceName))

      # add PvD-related IPv6 addresses
      if (pvdInfo.prefixes):
        for prefix in pvdInfo.prefixes:
          # TODO: PrefixInfo should contain IPAddress instead of str for prefix
          ipAddress = str(netaddr.EUI(mac).ipv6(netaddr.IPAddress(prefix.prefix)))
          ip.addr('add', index=ifaceIndex, address=ipAddress, prefixlen=prefix.prefixLength, rtproto='RTPROT_RA', family=socket.AF_INET6)
          LOG.debug('IP address {0}/{1} on {2} configured'.format(ipAddress, prefix.prefixLength, ifaceName))

      # add PvD-related routes
      if (pvdInfo.routes):
        for route in pvdInfo.routes:
          # some routes may be added during interface prefix configuration, skip them if already there
          try:
            # TODO: RouteInfo should contain IPAddress instead of str for prefix
            # TODO: PvdInfo should contain IPAddress instead of str for routerAddress
            ip.route('add', dst=route.prefix, mask=route.prefixLength, gateway=pvdInfo.routerAddress, oif=ifaceIndex, rtproto='RTPROT_RA', family=socket.AF_INET6)
            LOG.debug('route to {0}/{1} via {2} on {3} configured'.format(route.prefix, route.prefixLength, pvdInfo.routerAddress, ifaceName))
          except:
            LOG.warning('cannot configure route to {0}/{1} via {2} on {3}'.format(route.prefix, route.prefixLength, pvdInfo.routerAddress, ifaceName))

      # add link-local route
      try:
        ip.route('add', dst=self.__LINK_LOCAL_PREFIX, mask=self.__LINK_LOCAL_PREFIX_LENGTH, oif=ifaceIndex, rtproto='RTPROT_RA', family=socket.AF_INET6)
        LOG.debug('link-local route to {0}/{1} on {2} configured'.format(self.__LINK_LOCAL_PREFIX, self.__LINK_LOCAL_PREFIX_LENGTH, ifaceName))
      except:
        LOG.warning('cannot configure link-local route to {0}/{1} on {2}'.format(self.__LINK_LOCAL_PREFIX, self.__LINK_LOCAL_PREFIX_LENGTH, ifaceName))

      # add default route
      try:
        ip.route('add', dst=self.__DEFAULT_ROUTE_ADDRESS, gateway=pvdInfo.routerAddress, oif=ifaceIndex, rtproto='RTPROT_RA', family=socket.AF_INET6)
        LOG.debug('default route via {0} on {1} configured'.format(pvdInfo.routerAddress, ifaceName))
      except:
        LOG.warning('cannot configure default route via {0} on {1}'.format(pvdInfo.routerAddress, ifaceName))


  def __configureDns(self, pvdInfo, netnsName):
    # configure DNS data in resolv.conf
    if (pvdInfo):
      # delete existing resolv.conf file for a given namespace
      (dnsConfDir, dnsConfFile) = self.__getDnsConfPath(netnsName)
      shutil.rmtree(dnsConfDir, True)

      if (pvdInfo.rdnsses or pvdInfo.dnssls):
        # create new resolv.conf file for a given namespace
        os.makedirs(dnsConfDir)
        dnsConfFile = open(dnsConfFile, 'w')
        dnsConfFile.write('# Autogenerated by pvdman\n')
        dnsConfFile.write('# PvD ID: ' + pvdInfo.pvdId + '\n\n')

        if (pvdInfo.rdnsses):
          for rdnss in pvdInfo.rdnsses:
            if (rdnss.addresses):
              dnsConfFile.write('\n'.join('{} {}'.format('nameserver', address) for address in rdnss.addresses) + '\n\n')
          LOG.debug('RDNSS in {0} configured'.format(dnsConfFile))

        if (pvdInfo.dnssls):
          for dnssl in pvdInfo.dnssls:
            if (dnssl.domainNames):
              dnsConfFile.write('search ' + ' '.join('{}'.format(domainName) for domainName in dnssl.domainNames))
          LOG.debug('DNSSL in {0} configured'.format(dnsConfFile))


  def __createPvd(self, phyIfaceName, pvdInfo):
    phyIfaceIndex = self.ipRoot.link_lookup(ifname=phyIfaceName)
    if (len(phyIfaceIndex) > 0):
      phyIfaceIndex = phyIfaceIndex[0]
      if (self.pvds.get((phyIfaceName, pvdInfo.pvdId)) is None):
        # create a new network namespace to isolate the PvD configuration
        (netnsName, pvdIfaceName, ip) = self.__createNetns(phyIfaceIndex)
        # create a record to track the configured PvDs
        pvd = Pvd(pvdInfo.pvdId, pvdInfo, phyIfaceName, pvdIfaceName, netnsName)
        # configure the network namespace with the data received in RA message
        self.__configureNetwork(pvdIfaceName, pvdInfo, ip)
        self.__configureDns(pvdInfo, netnsName)
        # if PvD configuration completed successfully, add PvD record to the PvD manager's log
        self.pvds[(phyIfaceName, pvd.pvdId)] = pvd
        LOG.info('PvD {0} received through {1} CONFIGURED in network namespace {2} on macvlan {3}, type {4}'.format(pvd.pvdId, pvd.phyIfaceName, pvd.netnsName, pvd.pvdIfaceName, pvd.pvdInfo.pvdType))
      else:
        raise Exception('PvD duplicate error: PvD {0} is already configured on {1}'.format(pvdInfo.pvdId, phyIfaceName))
    else:
      raise Exception('Interface {0} does not exist'.format(phyIfaceName))


  def __updatePvd(self, phyIfaceName, pvdInfo):
    pvd = self.pvds.get((phyIfaceName, pvdInfo.pvdId))
    if (pvd):
      if (pvd.pvdInfo == pvdInfo):
        # if PvD parameters did not change, just update the timestamp in the PvD manager's log
        pvd.updateTimestamp()
        LOG.info('PvD {0} received through {1} UNCHANGED, timestamp UPDATED, type {2}'.format(pvd.pvdId, pvd.phyIfaceName, pvd.pvdInfo.pvdType))
      else:
        # if any of the PvD parameters has changed, reconfigure the PvD
        netns.setns(pvd.netnsName)
        ip = IPRoute()
        # return to a default network namespace to not cause a colision with other modules
        # ip handle continues to work in the target network namespace
        netns.setns(self.__NETNS_DEFAULT_NAME)
        self.__configureNetwork(pvd.pvdIfaceName, pvdInfo, ip)
        self.__configureDns(pvdInfo, pvd.netnsName)
        # update the PvD record in the PvD manager's log
        pvd.pvdInfo = pvdInfo
        pvd.updateTimestamp()
        LOG.info('PvD {0} received through {1} RECONFIGURED in network namespace {2} on macvlan {3}, type {4}'.format(pvd.pvdId, pvd.phyIfaceName, pvd.netnsName, pvd.pvdIfaceName, pvd.pvdInfo.pvdType))
    else:
      raise Exception('There is no PvD {0} configured on {1}'.format(pvdInfo.pvdId, phyIfaceName))


  def __removePvd(self, phyIfaceName, pvdId):
    pvd = self.pvds.get((phyIfaceName, pvdId))
    if (pvd):
      # remove the network namespace associated with the PvD (this in turn removes the PvD network configuration as well)
      if (pvd.netnsName in netns.listnetns()):
        netns.remove(pvd.netnsName)
      # remove the directory containing PvD-related DNS information
      (dnsConfDir, dnsConfFile) = self.__getDnsConfPath(pvd.netnsName)
      if (os.path.exists(dnsConfDir)):
        shutil.rmtree(dnsConfDir, True)
      # remove the PvD record from the PvD manager's log
      del self.pvds[(phyIfaceName, pvdId)]
      LOG.info('PvD {0} received through {1} REMOVED, network namespace {2} deleted, DNS directory {3} deleted, type {4}'.format(pvd.pvdId, pvd.phyIfaceName, pvd.netnsName, dnsConfDir, pvd.pvdInfo.pvdType))
    else:
      raise Exception('There is no PvD {0} configured on {1}'.format(pvdInfo.pvdId, phyIfaceName))


  '''
  PUBLIC METHODS
  '''

  def setPvd(self, phyIfaceName, pvdInfo):
    '''
    Configures the PvD parameters associated with a given physical network interface.
    This function is idempotent and can be safely invoked multiple times with the same or different parameters.
    If no PvD with a given ID is configured on a given interface, new PvD will be created.
    If PvD with a given ID is already configured on the interface, PvD parameters will be reconfigured if necessary.
    '''
    if (self.pvds.get((phyIfaceName, pvdInfo.pvdId)) is None):
      self.__createPvd(phyIfaceName, pvdInfo)
    else:
      self.__updatePvd(phyIfaceName, pvdInfo)


  def removePvd(self, phyIfaceName, pvdId):
    self.__removePvd(phyIfaceName, pvdId)


  def listPvds(self):
    pvdData = []
    for pvdKey, pvd in self.pvds.items():
      pvdData.append((pvd.phyIfaceName, pvd.pvdId))
    return pvdData


  def getPvds(self):
    pvdData = []
    for pvdKey, pvd in self.pvds.items():
      pvdData.append((pvd.pvdId, pvd.netnsName, pvd.phyIfaceName))
    return pvdData


  def getPvdInfo(self, phyIfaceName, pvdId):
    return self.pvds.get((phyIfaceName, pvdId))


  def cleanup(self):
    LOG.debug('PvdManager cleanup started')
    # create a deep copy of dictionary keys before deletion because Python cannot delete dictionary items while iterating over them
    pvdKeys = [key for key in self.pvds.keys()]
    for (phyIfaceName, pvdId) in pvdKeys:
      self.__removePvd(phyIfaceName, pvdId)
    # remove a symbolic link to a default network namespace
    self.__removeDefaultNetnsSymlink()
    LOG.debug('PvdManager cleanup finished')
