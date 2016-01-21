import os
import shutil
import time
import socket
import netaddr
import atexit
from pvdinfo import *
from pyroute2 import netns
from pyroute2 import IPRoute
from pyroute2 import IPDB

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


class PvdManager:
  __NETNS_PREFIX = 'mifpvd-'
  __netnsIdGenerator = 0;
  __PVD_IFACE_PREFIX = 'mifpvd-'
  __pvdIfaceIdGenerator = 0;
  __DNS_CONF_FILE = '/etc/netns/%NETNS_NAME%/resolv.conf'

  __NETNS_DEFAULT_PROC = '/proc/1/ns/net'
  __NETNS_DEFAULT_NAME = 'mifpvd-default'
  
  '''
  PRIVATE METHODS
  '''

  def __init__(self):
    self.pvds = {}
    self.ipRoot = IPRoute()
    self.ipdbRoot = IPDB()
    self.ipdbRoot.register_callback(self.__onIfaceStateChange)

    # create a symbolic link to be able to return to a default network namespace
    netnsDir = netns.NETNS_RUN_DIR
    if (not netnsDir.endswith('/')):
      netnsDir += '/'
    linkNetnsDefault = netnsDir + self.__NETNS_DEFAULT_NAME
    if (not os.path.exists(netnsDir)):
      os.makedirs(netnsDir)
    if (os.path.exists(linkNetnsDefault) and os.path.islink(linkNetnsDefault)):
      os.unlink(linkNetnsDefault)
    os.symlink(self.__NETNS_DEFAULT_PROC, linkNetnsDefault)

    # register a cleanup handler to remove configured PvDs and associated components at exit
    atexit.register(self.cleanup)


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
        print netnsName + ': ' + ifaceName + ' ADDED, state: ' + ifaceState
      elif (action == 'RTM_DELLINK'):
        print netnsName + ': ' + ifaceName + ' DELETED, state: ' + ifaceState
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
    dnsConfFile = self.__DNS_CONF_FILE.replace('%NETNS_NAME%', netnsName)
    dnsConfDir = dnsConfFile[0:dnsConfFile.rfind('/')]
    return (dnsConfDir, dnsConfFile)


  def __createNetns(self, phyIfaceIndex):
    netnsName = self.__getNetnsName()
    pvdIfaceName = self.__getPvdIfaceName()
    netns.create(netnsName)

    # create a virtual interface where PvD parameters are going to be configured, then move the interface to the new network namespace
    self.ipRoot.link_create(ifname=pvdIfaceName, kind='macvlan', link=phyIfaceIndex)
    pvdIfaceIndex = self.ipRoot.link_lookup(ifname=pvdIfaceName)
    self.ipRoot.link('set', index=pvdIfaceIndex[0], net_ns_fd=netnsName)
    
    # change the namespace and get new NETLINK handles to operate in new namespace
    netns.setns(netnsName)
    ip = IPRoute()
    ipdb = IPDB()
    ipdb.register_callback(self.__onIfaceStateChange)
    # return to a default network namespace to not cause a colision with other modules
    # ip and ipdb handles continue to work in the target network namespace
    netns.setns(self.__NETNS_DEFAULT_NAME)

    # get new index since interface has been moved to a different namespace
    loIfaceIndex = ip.link_lookup(ifname='lo')
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

      # get interface MAC address to derive the IPv6 address from
      iface = ip.get_links(ifaceIndex)[0]
      mac = iface.get_attr('IFLA_ADDRESS')
      if (pvdInfo.prefixes):
        for prefix in pvdInfo.prefixes:
          # TODO: PrefixInfo should contain IPAddress instead of str
          ipAddress = str(netaddr.EUI(mac).ipv6(netaddr.IPAddress(prefix.prefix)))
          ip.addr('add', index=ifaceIndex, address=ipAddress, prefixlen=prefix.prefixLength, family=socket.AF_INET6)

      if (pvdInfo.routes):
        for route in pvdInfo.routes:
          # some routes may be added during interface prefix configuration, skip them if already there
          try:
            ip.route('add', dst=route.prefix, mask=route.prefixLength, oif=ifaceIndex, rtproto='RTPROT_STATIC', rtscope='RT_SCOPE_LINK', family=socket.AF_INET6)
          except:
            pass


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

        if (pvdInfo.dnssls):
          for dnssl in pvdInfo.dnssls:
            if (dnssl.domainNames):
              dnsConfFile.write('search ' + ' '.join('{}'.format(domainName) for domainName in dnssl.domainNames))


  def __createPvd(self, phyIfaceName, pvdInfo):
    print('[' + time.strftime('%Y-%m-%d %H:%M:%S') + '] CREATING PvD ' + pvdInfo.pvdId + ' received on interface ' + phyIfaceName)
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
        print('[' + time.strftime('%Y-%m-%d %H:%M:%S') + '] PvD ' + pvdInfo.pvdId + ' received on interface ' + phyIfaceName +
              ' CONFIGURED in namespace ' + netnsName + ', macvlan interface ' + pvdIfaceName)
      else:
        raise Exception('PvD duplicate error: PvD with ID ' + pvdInfo.pvdId + ' is already configured on ' + phyIfaceName + '.')
    else:
      raise Exception('Interface ' + phyIfaceName + ' does not exist.')


  def __updatePvd(self, phyIfaceName, pvdInfo):
    print('[' + time.strftime('%Y-%m-%d %H:%M:%S') + '] UPDATING PvD ' + pvdInfo.pvdId + ' received on interface ' + phyIfaceName)
    pvd = self.pvds.get((phyIfaceName, pvdInfo.pvdId))
    if (pvd):
      if (pvd.pvdInfo == pvdInfo):
        # if PvD parameters did not change, just update the timestamp in the PvD manager's log
        pvd.updateTimestamp()
        print('[' + time.strftime('%Y-%m-%d %H:%M:%S') + '] PvD ' + pvdInfo.pvdId + ' received on interface ' + phyIfaceName +
              ': NO CHANGE in parameters, timestamp UPDATED')
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
        print('[' + time.strftime('%Y-%m-%d %H:%M:%S') + '] PvD ' + pvdInfo.pvdId + ' received on interface ' + phyIfaceName +
              ' RECONFIGURED in namespace ' + pvd.netnsName + ', macvlan interface ' + pvd.pvdIfaceName)
    else:
      raise Exception('There is no PvD with ID ' + pvdInfo.pvdId + ' configured on ' + phyIfaceName + '.')


  def __removePvd(self, phyIfaceName, pvdId):
    print('[' + time.strftime('%Y-%m-%d %H:%M:%S') + '] REMOVING PvD ' + pvdId + ' received on interface ' + phyIfaceName)
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
      print('[' + time.strftime('%Y-%m-%d %H:%M:%S') + '] PvD ' + pvd.pvdId + ' received on interface ' + pvd.phyIfaceName +
            ' REMOVED, namespace ' + pvd.netnsName + ' deleted, DNS directory ' + dnsConfDir + ' deleted')
    else:
      raise Exception('There is no PvD with ID ' + pvdInfo.pvdId + ' configured on ' + phyIfaceName + '.')


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


  def getPvdInfo(self, phyIfaceName, pvdId):
    return self.pvds.get((phyIfaceName, pvdId))


  def cleanup(self):
    # create a deep copy of dictionary keys before deletion because Python cannot delete dictionary items while iterating over them
    pvdKeys = [key for key in self.pvds.keys()]
    for (phyIfaceName, pvdId) in pvdKeys:
      self.__removePvd(phyIfaceName, pvdId)
