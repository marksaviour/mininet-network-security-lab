#!/usr/bin/env python
from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call
import subprocess

def myNetwork():
    net = Mininet( topo=None,
                   build=False,
                   ipBase='10.0.0.0/8')

    info( '*** Adding controller\n' )
    c0 = net.addController(name='Controller',
                           controller=OVSController,
                           protocol='tcp',
                           port=6633)

    info( '*** Add switches\n')
    Switch1 = net.addSwitch('Switch1', cls=OVSKernelSwitch)

    info( '*** Add router\n')
    Router1 = net.addHost('Router1', cls=Node, ip='0.0.0.0')

    info( '*** Add hosts\n')
    # The-Internet (Server) - 192.168.2.100
    # Using short name "Server" to stay within 15-char interface name limit
    Server = net.addHost('Server', cls=Host, ip='192.168.2.100/24', defaultRoute='via 192.168.2.1')

    # PCs on the LAN - 192.168.0.0/24 network
    PC1 = net.addHost('PC1', cls=Host, ip='192.168.0.2/24', defaultRoute='via 192.168.0.1')
    PC2 = net.addHost('PC2', cls=Host, ip='192.168.0.3/24', defaultRoute='via 192.168.0.1')
    PC3 = net.addHost('PC3', cls=Host, ip='192.168.0.4/24', defaultRoute='via 192.168.0.1')

    info( '*** Add links\n')
    # LAN side: PCs connect to Switch
    net.addLink(PC1, Switch1)
    net.addLink(PC2, Switch1)
    net.addLink(PC3, Switch1)

    # Switch connects to Router
    net.addLink(Router1, Switch1)

    # Router connects to Server (The-Internet)
    net.addLink(Router1, Server)

    info( '*** Starting network\n')
    net.build()

    info( '*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info( '*** Starting switches\n')
    net.get('Switch1').start([c0])

    info( '*** Configuring router\n')
    # Enable IP forwarding on Router1
    Router1.cmd('sysctl -w net.ipv4.ip_forward=1')

    # Router1 LAN interface (towards Switch1) - 192.168.0.1
    Router1.cmd('ip addr add 192.168.0.1/24 dev Router1-eth0')

    # Router1 WAN interface (towards Server) - 192.168.2.1
    Router1.cmd('ip addr add 192.168.2.1/24 dev Router1-eth1')

    info( '*** Configuring NAT for internet access\n')
    subprocess.call(['sysctl', '-w', 'net.ipv4.ip_forward=1'])
    subprocess.call(['iptables', '-t', 'nat', '-A', 'POSTROUTING',
                     '-s', '192.168.0.0/24', '-o', 'enp0s5', '-j', 'MASQUERADE'])

    # Give router a default route out via host gateway
    Router1.cmd('ip route add default via 10.211.55.1 dev Router1-eth0')

    info( '*** Network ready\n')
    info( '*** Extended Star Topology Network\n')
    info( '*** Server = "The-Internet" (192.168.2.100)\n')
    info( '*** Test with: PC1 ping PC2 | PC1 ping PC3 | PC1 ping Server\n')

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    myNetwork()
