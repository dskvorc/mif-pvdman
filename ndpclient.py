# simple NDP client that reads NDP messages
# - emphasis is on processing PVD_CO options

# formated with tab=4 spaces long (not replaced with spaces)

import socket, select, struct, sys, binascii, json
import pyroute2, ipaddress, logging, hashlib, uuid
import pvdinfo

# initialize logger
logging.basicConfig(level=logging.DEBUG,
format='%(asctime)s %(filename)s:%(lineno)d %(levelname)s %(name)s - %(message)s')
LOG = logging.getLogger(__name__)


class NDPClient:
	def __init__ ( self, iface = None, lla = None ):
		self.iface = iface # interface identifier, e.g. "eth0"
		self.__lla = lla     # local-link ipv6 address
		# open raw socket for icmpv6 messages
		self.__sock = socket.socket ( socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_ICMPV6 )
		self.__sock.setsockopt ( socket.IPPROTO_IPV6, socket.IPV6_RECVPKTINFO, 1 )
		self.__sock.setsockopt ( socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 255 )
		if self.iface:
			self.__sock.setsockopt ( socket.SOL_SOCKET, 25, bytes(iface, 'UTF-8') )

	def __del__(self):
		self.__sock.close()

	def get_sock ( self ):
		'''Return socket used by this object'''
		return self.__sock

	def get_pvdinfo ( self, timeout = 0 ):
		'''If got information from RA pack them into PvdInfo class'''
		msg = self.recvmsg ( timeout )
		if not msg or msg.Type != NdpMsg.TYPE_RA:
			return None

		# get additional PVD parameters from router
		prop = self.__get_pvd_description ( msg.src, msg.iface )
		#print(prop)

		# create PvdInfo structs from received RA
		pvdinfos = []

		# create implicit pvd info
		# pvdId = "implicit"
		( pvdId, mtu, prefixes, routes, rdnsses, dnssls ) = \
			NDPClient.__prepare_options_for_pvd ( msg.options )
		# which elements must be present for implicit pvd to be created? TODO
		pvdId = NDPClient.__create_uuid ( mtu, prefixes, routes, rdnsses, dnssls )
		pvd_properties = None
		if prop:
			for p in prop:
				if p["PVD_ID"] == "implicit":
					pvd_properties = p
					break

		LOG.debug ( "Adding implicit pvd: " + str(pvdId) )
		pvdInfo = pvdinfo.PvdInfo ( pvdId, pvdinfo.PvdType.IMPLICIT, msg.src,
				mtu, prefixes, routes, rdnsses, dnssls, [], [], pvd_properties )
		pvdinfos.append ( ( msg.iface, pvdInfo ) )

		# Do we have PVD_CO option?
		for opt in msg.options:
			if opt['type'] == NdpMsg.OPT_PVD_CO:
				( pvdId, mtu, prefixes, routes, rdnsses, dnssls ) = \
					NDPClient.__prepare_options_for_pvd ( opt['options'] )

				pvd_properties = None
				if prop:
					for p in prop:
						if p["PVD_ID"] == pvdId:
							pvd_properties = p
							break

				LOG.debug ( "Adding pvd: " + str(pvdId) )
				pvdInfo = pvdinfo.PvdInfo ( pvdId, pvdinfo.PvdType.EXPLICIT,
					msg.src, mtu, prefixes, routes, rdnsses, dnssls, [], [],
					pvd_properties )
				pvdinfos.append ( ( msg.iface, pvdInfo ) )

		return pvdinfos

	@staticmethod
	def __get_pvd_description ( src, from_iface ):
		try:
			addrinfo = socket.getaddrinfo(src+"%"+from_iface, 8080, 0, socket.SOCK_STREAM)
			(family, socktype, proto, canonname, sockaddr) = addrinfo[0]
			s = socket.socket(family, socktype, proto)
			s.connect(sockaddr)
			s.send(b'GET /pvd-info.json\r\n\r\n')
			return json.loads(s.recv(10240).decode("utf-8") )
		except:
			return None

	@staticmethod
	def __prepare_options_for_pvd ( options ):
		pvdId = None
		mtu = None
		prefixes = []
		routes = []
		rdnsses = []
		dnssls = []
		for pvd_opt in options:
			if pvd_opt['type'] == NdpMsg.OPT_PVD_ID:
				pvdId = pvd_opt['pvdId']

			elif pvd_opt['type'] == NdpMsg.OPT_MTU:
				mtu = pvd_opt['MTUInfo']

			elif pvd_opt['type'] == NdpMsg.OPT_PREFIX:
				prefixes.append ( pvd_opt['PrefixInfo'] )

			elif pvd_opt['type'] == NdpMsg.OPT_ROUTE:
				routes.append ( pvd_opt['RouteInfo'] )

			elif pvd_opt['type'] == NdpMsg.OPT_RDNSS:
				rdnsses.append ( pvd_opt['RDNSSInfo'] )

			elif pvd_opt['type'] == NdpMsg.OPT_DNSSL:
				dnssls.append ( pvd_opt['DNSSLInfo'] )

		return ( pvdId, mtu, prefixes, routes, rdnsses, dnssls )

	@staticmethod
	def __create_uuid ( mtu, prefixes, routes, rdnsses, dnssls ):
		data = str(mtu)
		for prefix in prefixes:
			data += prefix.prefix
		for route in routes:
			data += route.prefix
		for rdn in rdnsses:
			for address in rdn.addresses:
				data += address
		for dns in dnssls:
			for domain in dns.domainNames:
				data += domain
		digest = hashlib.sha1 ( data.encode('utf-8') ).digest()
		return str ( uuid.UUID ( bytes = digest[:16] ) )

	def send_rs ( self, pvdId = None, iface = None, src = None, dest = None ):
		'''Send Router-Solicitation message'''
		_iface = iface or self.iface
		if not _iface:
			# error, or should RS be sent to all interfaces by default?
			LOG.error("Interface must be provided for RS!")
			return None

		_src = src or self.__lla
		if not _src:
			# get ip address from interface with pyroute2
			ip = pyroute2.IPDB()
			if _iface in ip.interfaces and 'ipaddr' in ip.interfaces[_iface]:
				for i in range(len(ip.interfaces[_iface]['ipaddr'])):
					a = ip.interfaces[_iface]['ipaddr'][i]
					if 'address' in a:
						ipaddr = ipaddress.ip_address ( a['address'] )
						if ipaddr.is_link_local and ipaddr.version == 6:
							_src = a['address']
							break
			if not _src:
				LOG.error("Source address must be provided!")
				return None

		msg = NdpMsg.create_rs ( src = _src, dest = dest, pvdId = pvdId, iface = _iface )
		addr = ( msg.dest, 0, 0, socket.if_nametoindex(_iface) )
		self.__sock.sendto ( msg.packet, addr )
		return msg

	def recvmsg ( self, timeout = 0 ):
		( r, w, x ) = select.select ( [self.__sock], [], [], timeout )
		if not r:
			return None
		(packet, ancdata, msg_flags, address) = self.__sock.recvmsg ( 65536, 1024 )
		# packet = NDP packet
		# address = (host, port, flowinfo, scopeid)
		src = address[0].split("%")[0]
		dest = None
		iface_id = address[3]
		# ancdata = (cmsg_level, cmsg_type, cmsg_data)
		# cmsg_data =  struct in6_pktinfo{ struct in6_addr ipi6_addr; int ipi6_ifindex;}
		for (cmsg_level, cmsg_type, cmsg_data) in ancdata:
			if cmsg_level == socket.IPPROTO_IPV6 and cmsg_type == socket.IPV6_PKTINFO and cmsg_data:
				dest = socket.inet_ntop ( socket.AF_INET6, cmsg_data[:-4] )
				iface_id = int.from_bytes(cmsg_data[-4:], byteorder=sys.byteorder)
				break

		#LOG.debug("NDP packet received through interface " + str(iface_id))
		iface = socket.if_indextoname(iface_id)
		return NdpMsg.from_packet ( packet, src, dest, iface )

# NDP message handling
class NdpMsg: # rfc4861
	ALL_ROUTERS = "ff02::2"
	TYPE_RS = 133
	TYPE_RA = 134
	OPT_SRC_LLA = 1
	OPT_TARG_LLA = 2
	OPT_PREFIX = 3
	OPT_REDIRECT = 4
	OPT_MTU = 5
	OPT_PVD_CO = 63        # (TBD) draft-ietf-mif-mpvd-ndp-support-02
	OPT_PVD_ID = 64        # (TBD) draft-ietf-mif-mpvd-ndp-support-02
	OPT_ROUTE = 24         # rfc4191
	OPT_RDNSS = 25         # rfc6106
	OPT_DNSSL = 31         # rfc6106
	OPT_LoWPANContext = 34 # rfc6775 (not implemented)
	OPT_ABRO = 35          # rfc6775 (not implemented)

	def __init__ ( self, src = None, dest = None, iface = None ):
		self.src = src
		self.dest = dest
		self.iface = iface
		self.options = []

	@classmethod
	def from_packet ( cls, packet, src, dest, iface ):
		if not packet or not src or not dest:
			return None
		if NdpMsg.__checksum ( src, dest, len(packet), 58, packet ) != 0xffff:
			LOG.error("Checksum error")
			return None
		msg = cls ( src, dest, iface )
		msg.packet = packet
		#unpack
		options = b''
		(msg.Type, msg.Code, msg.Checksum) = struct.unpack("!BBH", packet[0:4])
		if msg.Type == NdpMsg.TYPE_RA:
			(msg.Hop_Limit, MO, msg.Router_Lifetime, msg.Reachable_Time,
			 msg.Retrans_Timer) = struct.unpack("!BBHII", packet[4:16])
			msg.M = ( MO & 0x80 ) != 0
			msg.O = ( MO & 0x40 ) != 0
			if len(packet) > 16:
				options = packet[16:]
		elif msg.Type == NdpMsg.TYPE_RS:
			if len(packet) > 8:
				options = packet[8:]
		else:
			#LOG.debug("`	")
			return None
		if NdpMsg.__unpack_options ( msg.options, options ):
			return msg
		else:
			return None

	@staticmethod
	def __unpack_options ( save_to, options, encapsulated = False ):
		''' Unpack options from raw form 'options' to list 'save_to' '''
		# each unpacked options have: type, len, raw 'data' and formated data
		# which is named per option type (e.g. for OPT_MTU => name is 'mtu')

		have_pvd_id = False # used only for encapsulated options within OPT_PVD_CO

		while options:
			opt={}
			opt['type'] = options[0]
			opt['len'] = options[1]
			opt['data'] = options[2:opt['len']*8]
			options = options[opt['len']*8:]
			if opt['type'] == NdpMsg.OPT_SRC_LLA:
				opt['src_lla'] = opt['data']

			elif opt['type'] == NdpMsg.OPT_TARG_LLA:
				opt['targ_lla'] = opt['data']

			elif opt['type'] == NdpMsg.OPT_PREFIX:
				opt['PrefixInfo'] = pvdinfo.PrefixInfo (
					opt['data'][0],
					( opt['data'][1] & 0x80 ) != 0,
					( opt['data'][1] & 0x40 ) != 0,
					struct.unpack("!I", opt['data'][2:6])[0],
					struct.unpack("!I", opt['data'][6:10])[0],
					socket.inet_ntop ( socket.AF_INET6, opt['data'][14:])
				)

			elif opt['type'] == NdpMsg.OPT_REDIRECT:
				pass # don't process this option (for now)

			elif opt['type'] == NdpMsg.OPT_MTU:
				opt['MTUInfo'] = MTUInfo ( struct.unpack("!I", opt['data'][2:6]) )

			elif opt['type'] == NdpMsg.OPT_PVD_CO:
				if encapsulated:
					LOG.error("Container inside container")
					return False
				opt['S'] = ( (opt['data'][0] & 0x80 ) != 0 )
				opt['Name_Type'] = opt['data'][1]
				if opt['S']:
					#opt['key_hash'] = opt['data][2:18]
					#must proces signature for length ..
					#container = opt['data'] + skip hash and signature
					pass
				else:
					container = opt['data'][6:]
				opt['options'] = []
				if not NdpMsg.__unpack_options ( opt['options'], container, True ):
					return False

			elif opt['type'] == NdpMsg.OPT_PVD_ID:
				if encapsulated and have_pvd_id:
					LOG.error("Multiple PVD_ID inside single container")
					return False
				have_pvd_id = True
				opt['pvdId'] = (opt['data'][2:]).decode("utf-8")

			elif opt['type'] == NdpMsg.OPT_ROUTE:
				opt['RouteInfo'] = pvdinfo.RouteInfo (
					opt['data'][0], #prefixLength
					( opt['data'][1] >> 3 ) & 0x3, # routePreference
					struct.unpack("!I", opt['data'][2:6])[0], # routeLifetime
					socket.inet_ntop ( socket.AF_INET6, opt['data'][6:]) # prefix
				)

			elif opt['type'] == NdpMsg.OPT_RDNSS:
				lifetime = struct.unpack("!I", opt['data'][2:6])[0]
				addresses = []
				addr = opt['data'][6:]
				while addr:
					addresses.append ( socket.inet_ntop ( socket.AF_INET6, addr[:16] ) )
					addr = addr[16:]
				opt['RDNSSInfo'] = pvdinfo.RDNSSInfo ( lifetime, addresses )

			elif opt['type'] == NdpMsg.OPT_DNSSL:
				lifetime = struct.unpack("!I", opt['data'][2:6])[0]
				domains = []
				d = opt['data'][6:]
				while d and d[0] > 0:
					domain = d[1:d[0]+1].decode('utf-8')
					d = d[d[0]+1:]
					while d and d[0] != 0:
						domain += "." + d[1:d[0]+1].decode('utf-8')
						d = d[d[0]+1:]
					domains.append ( domain )
					if d and d[0] == 0:
						d = d[1:]
				opt['DNSSLInfo'] = pvdinfo.DNSSLInfo ( lifetime, domains )

			else:
				#don't process unknown options
				pass
			save_to.append(opt)

		return True

	@classmethod
	def create_rs ( cls, src, dest = None, pvdId = None, iface = None ):
		dest = dest or NdpMsg.ALL_ROUTERS
		if not src or not dest: # required for checksum
			return None
		msg = cls ( src, dest, iface )
		msg.pvdId = pvdId
		msg.Type = NdpMsg.TYPE_RS
		msg.Code = 0

		msg.packet = struct.pack ( "BBHI", msg.Type, msg.Code, 0, 0 )
		if pvdId:
			if isinstance ( pvdId, list ): pvds = pvdId
			else: 	pvds = [pvdId]
			for pvd in pvds:
				# TODO update if pvd can be something other than uuid
				pvdId_type = 1
				pvdId_uuid = bytes ( pvd, 'utf-8' )
				pvdId_len = len(pvdId_uuid)

				pvdId_opt = struct.pack("BB", pvdId_type, pvdId_len )
				pvdId_opt += pvdId_uuid
				opt_len = 2 + ( 2 + pvdId_len )
				pad_len = ((opt_len+7)//8)*8 - opt_len
				pvdId_opt += (b'\0')*pad_len
				opt_len = (2 + ( 2 + len(pvdId_opt) ))//8

				msg.packet += struct.pack("BB", NdpMsg.OPT_PVD_ID, opt_len )
				msg.packet += pvdId_opt
				msg.options.append ( { 'type':NdpMsg.OPT_PVD_ID, 'len':opt_len, 'data':pvdId_opt, 'pvdId':pvd } )

		chks = NdpMsg.__checksum ( msg.src, msg.dest, len(msg.packet), 58, msg.packet )
		msg.packet = msg.packet[0:2] + struct.pack ( "!H", chks ) + msg.packet[4:]
		return msg

	@staticmethod
	def __checksum ( src, dest, length, next_header, packet ):
		p =  socket.inet_pton ( socket.AF_INET6, src )
		p += socket.inet_pton ( socket.AF_INET6, dest )
		p += struct.pack ( "!LBBBB", length, 0,0,0, next_header ) + packet
		csum = 0
		for i in range ( 0, len(p), 2 ):
			csum += int.from_bytes ( p[i:i+2], byteorder="big" )
		while csum > 1<<16:
			csum = (csum>>16) + (csum&0xffff)
		return csum

# rest is only for debugging
	def dump(self):
		s = "src:"+str(self.src)+"\ndest:"+str(self.dest)
		if self.iface:
			s += "\niface="+self.iface
		s += "\nNDP:"
		if self.Type == NdpMsg.TYPE_RA:
			s += "\n\tMessage Type: Router Advertisement message"
		elif self.Type == NdpMsg.TYPE_RS:
			s += "\n\tMessage Type: Router Solicitation message"
		s += "\n\tType:"+str(self.Type)+"\n\tCode:" + str(self.Code)
		if self.Type == NdpMsg.TYPE_RA:
			s += "\n\tCur Hop Limit:" + str(self.Hop_Limit)
			s += "\n\tM:" + str(self.M)
			s += "\n\tO:" + str(self.O)
			s += "\n\tRouter Lifetime:" + str(self.Router_Lifetime)
			s += "\n\tReachable Time:" + str(self.Reachable_Time)
			s += "\n\tRetrans Timer:" + str(self.Retrans_Timer)
			s += "\n\tRouter Lifetime:" + str(self.Router_Lifetime)
		s += NdpMsg.__dump_options ( self.options )
		return s

	@staticmethod
	def __dump_options ( options ):
		s = ""
		for opt in options:
			s += "\n\toption: "
			if opt['type'] == NdpMsg.OPT_PVD_ID:
				s += "OPT_PVD_ID " + str(opt['pvdId']) + "\n"
			elif opt['type'] == NdpMsg.OPT_SRC_LLA:
				s += "Source Link-layer Address:" + "\n\t\t"
				s += binascii.hexlify ( opt['data'] ).decode('utf-8')
			elif opt['type'] == NdpMsg.OPT_TARG_LLA:
				s += "Target  Link-layer Address:" + "\n\t\t"
				s += binascii.hexlify ( opt['data'] ).decode('utf-8')
			elif opt['type'] == NdpMsg.OPT_PREFIX:
				s += "OPT_PREFIX " + "\n\t\t"
				s += "prefixLength:" + str(opt['PrefixInfo'].prefixLength) + "\n\t\t"
				s += "onLink:" + str(opt['PrefixInfo'].onLink) + "\n\t\t"
				s += "autoAddressConfig:" + str(opt['PrefixInfo'].autoAddressConfig) + "\n\t\t"
				s += "validLifetime:" + str(opt['PrefixInfo'].validLifetime) + "\n\t\t"
				s += "preferredLifetime:" + str(opt['PrefixInfo'].preferredLifetime) + "\n\t\t"
				s += "prefix:" + str(opt['PrefixInfo'].prefix) + "\n"
			elif opt['type'] == NdpMsg.OPT_MTU:
				s += "OPT_MTU " + str(opt['MTUInfo'].mtu)
			elif opt['type'] == NdpMsg.OPT_PVD_CO:
				s += "OPT_PVD_CO start >>>>>>>>>>>>>>>>>>>>>>>>>>>>>" + "\n\t\t"
				s += NdpMsg.__dump_options ( opt['options'] )
				s += "\n\toption: OPT_PVD_CO end <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<" + "\n"
			elif opt['type'] == NdpMsg.OPT_ROUTE:
				s += "OPT_ROUTE " + "\n\t\t"
				s += "prefixLength:" + str(opt['RouteInfo'].prefixLength) + "\n\t\t"
				s += "routePreference:" + str(opt['RouteInfo'].routePreference) + "\n\t\t"
				s += "preferred_lifetime:" + str(opt['RouteInfo'].routeLifetime) + "\n\t\t"
				s += "prefix:" + str(opt['RouteInfo'].prefix) + "\n"
			elif opt['type'] == NdpMsg.OPT_RDNSS:
				s += "OPT_RDNSS " + "\n\t\t"
				s += "lifetime:" + str(opt['RDNSSInfo'].lifetime) + "\n\t\t"
				s += "addresses:" + str(opt['RDNSSInfo'].addresses) + "\n"
			elif opt['type'] == NdpMsg.OPT_DNSSL:
				s += "OPT_DNSSL " + "\n\t\t"
				s += "lifetime:" + str(opt['DNSSLInfo'].lifetime) + "\n\t\t"
				s += "domainNames:" + str(opt['DNSSLInfo'].domainNames) + "\n"
			else:
				s += "(raw) " + str(opt['type']) +" " + str(opt['len']) + " "
				s += binascii.hexlify ( opt['data'] ).decode('utf-8') #str(opt['data'])
		return s

if __name__ == "__main__":
	# print ( "Usage: " + sys.argv[0] + " [iface [uuid-to-request]]" )
	iface = None
	if len(sys.argv) > 1:
		iface = sys.argv[1]

	ndpc = NDPClient( iface = iface )

	if len(sys.argv) > 2:
		uuid = sys.argv[2]
	else:
		uuid = None

	if iface:
		sent = ndpc.send_rs ( pvdId = uuid, iface = iface )
		print("\nSent:")
		print(sent.dump())

	#received = ndpc.get_pvdinfo ( timeout=30 )
	received = ndpc.recvmsg ( timeout=30 )
	if received:
		print("\nReceived:")
		print(received.dump())

# listen for first ndp packet:
# sudo python3 ndpclient.py

# send Router Solicitation message
# sudo python3 ndpclient.py eth1

# send Router Solicitation message
# (uuid of pvd to request: aff6ed92-b4a1-11e5-9f22-ba0be0483c18)
# sudo python3 ndpclient.py eth1 aff6ed92-b4a1-11e5-9f22-ba0be0483c18
