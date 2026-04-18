from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def build_topology():
    setLogLevel('info')
    net = Mininet(switch=OVSSwitch, controller=None, autoSetMacs=True)
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s3)
    net.addLink(h4, s3)
    net.addLink(s1, s2)
    net.addLink(s2, s3)
    net.start()
    info("\n===== TOPOLOGY STARTED =====\n")
    info("Hosts: h1=10.0.0.1  h2=10.0.0.2  h3=10.0.0.3  h4=10.0.0.4\n")
    info("Switches: s1 -- s2 -- s3\n")
    info("Controller: POX at 127.0.0.1:6633\n")
    return net

if __name__ == '__main__':
    net = build_topology()
    CLI(net)
    net.stop()
