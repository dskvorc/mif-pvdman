# https://tools.ietf.org/html/rfc4861
class MTUInfo:
  def __init__(self, mtu):
    # 32-bit unsigned integer
    self.mtu = mtu

  def __eq__(self, other):
    return self.mtu == other.mtu

  def __ne__(self, other):
    return not self == other


# https://tools.ietf.org/html/rfc4861
class PrefixInfo:
  def __init__(self, prefixLength, onLink, autoAddressConfig, validLifetime, preferredLifetime, prefix):
    # 8-bit unsigned integer
    self.prefixLength = prefixLength
    # True|False
    self.onLink = onLink
    # True|False
    self.autoAddressConfig = autoAddressConfig
    # 32-bit unsigned integer
    self.validLifetime = validLifetime
    # 32-bit unsigned integer
    self.preferredLifetime = preferredLifetime
    # netaddr.IPAddress
    self.prefix = prefix

  def __eq__(self, other):
    return (self.prefixLength == other.prefixLength and
            self.onLink == other.onLink and
            self.autoAddressConfig == other.autoAddressConfig and
            self.prefix == other.prefix)

  def __ne__(self, other):
    return not self == other


# https://tools.ietf.org/html/rfc4191
class RouteInfo:
  def __init__(self, prefixLength, routePreference, routeLifetime, prefix):
    # 8-bit unsigned integer
    self.prefixLength = prefixLength
    # 2-bit signed integer
    self.routePreference = routePreference
    # 32-bit unsigned integer
    self.routeLifetime = routeLifetime
    # netaddr.IPAddress
    self.prefix = prefix

  def __eq__(self, other):
    return (self.prefixLength == other.prefixLength and
            self.routePreference == other.routePreference and
            self.prefix == other.prefix)

  def __ne__(self, other):
    return not self == other


# https://tools.ietf.org/html/rfc6106
class RDNSSInfo:
  def __init__(self, lifetime, addresses):
    # 32-bit unsigned integer
    self.lifetime = lifetime
    # [] of netaddr.IPAddress
    self.addresses = addresses

  def __eq__(self, other):
    return self.addresses == other.addresses

  def __ne__(self, other):
    return not self == other


# https://tools.ietf.org/html/rfc6106
class DNSSLInfo:
  def __init__(self, lifetime, domainNames):
    # 32-bit unsigned integer
    self.lifetime = lifetime
    # [] of str
    self.domainNames = domainNames

  def __eq__(self, other):
    return self.domainNames == other.domainNames

  def __ne__(self, other):
    return not self == other


# https://tools.ietf.org/html/rfc6775
class LoWPANContextInfo:
  def __init__(self, contextLength, compression, contextId, validLifetime, contextPrefix):
    # 8-bit unsigned integer
    self.contextLength = contextLength
    # True|False
    self.compression = compression
    # 4-bit unsigned integer
    self.contextId = contextId
    # 16-bit unsigned integer
    self.validLifetime = validLifetime
    # netaddr.IPAddress
    self.contextPrefix = contextPrefix

  def __eq__(self, other):
    return (self.contextLength == other.contextLength and
            self.compression == other.compression and
            self.contextId == other.contextId and
            self.contextPrefix == other.contextPrefix)

  def __ne__(self, other):
    return not self == other


# https://tools.ietf.org/html/rfc6775
class ABROInfo:
  def __init__(self, versionLow, versionHigh, validLifetime, lbrAddress):
    # 32-bit unsigned integer (versionLow and versionHigh are 16-bit unsigned integers)
    self.version = versionHigh << 16 + versionLow;
    # 16-bit unsigned integer
    self.validLifetime = validLifetime
    # netaddr.IPAddress
    self.lbrAddress = lbrAddress

  def __eq__(self, other):
    return (self.version == other.version and
            self.lbrAddress == other.lbrAddress)

  def __ne__(self, other):
    return not self == other


class PvdInfo:
  def __init__(self, pvdId, mtu, prefixes, routes, rdnsses, dnssls, lowpancontexts, abros):
    # UUID
    self.pvdId = pvdId
    # MTUInfo
    self.mtu = mtu
    # [] of ***Info
    self.prefixes = prefixes
    self.routes = routes
    self.rdnsses = rdnsses
    self.dnssls = dnssls
    self.lowpancontexts = lowpancontexts
    self.abros = abros

  def __eq__(self, other):
    return (self.pvdId == other.pvdId and
            self.mtu == other.mtu and
            self.prefixes == other.prefixes and
            self.routes == other.routes and
            self.rdnsses == other.rdnsses and
            self.dnssls == other.dnssls and
            self.lowpancontexts == other.lowpancontexts and
            self.abros == other.abros)

  def __ne__(self, other):
    return not self == other
