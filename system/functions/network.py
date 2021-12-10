import socket

def cidr(address, addressRange):
    from netaddr import IPNetwork, IPAddress
    if type(addressRange) is list:
        for networkAddressRange in addressRange:
            if IPAddress(address) in IPNetwork(networkAddressRange):
                return True
    else:
        if IPAddress(address) in IPNetwork(addressRange):
            return True
    return False

def reverseDNS(IPv4Address):
    return socket.gethostbyaddr(IPv4Address)

def maskTocidr(netmask):
    from netaddr import IPAddress
    return IPAddress(netmask).netmask_bits()

