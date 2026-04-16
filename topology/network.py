from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI

class QoSTopology(Topo):
    def build(self):
        # Add switch
        s1 = self.addSwitch('s1',
                            cls=OVSSwitch,
                            protocols='OpenFlow13')

        # Add hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24')  # VoIP
        h2 = self.addHost('h2', ip='10.0.0.2/24')  # HTTP
        h3 = self.addHost('h3', ip='10.0.0.3/24')  # FTP

        # Add links with bandwidth limit to make QoS visible
        self.addLink(h1, s1, bw=10)
        self.addLink(h2, s1, bw=10)
        self.addLink(h3, s1, bw=10)

def run():
    setLogLevel('info')
    topo = QoSTopology()

    # Connect to Faucet controller
    net = Mininet(
        topo=topo,
        controller=RemoteController('faucet', ip='127.0.0.1', port=6653),
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True
    )

    net.start()

    # Set up QoS queues on the switch
    s1 = net.get('s1')
    for intf in s1.intfNames():
        if intf != 'lo':
            # Create 3 queues: high, medium, low
            s1.cmd(f'ovs-vsctl set port {intf} qos=@newqos '
                   f'-- --id=@newqos create qos type=linux-htb '
                   f'queues=0=@q0,1=@q1,2=@q2 '
                   f'-- --id=@q0 create queue other-config:min-rate=5000000 '
                   f'-- --id=@q1 create queue other-config:min-rate=3000000 '
                   f'-- --id=@q2 create queue other-config:min-rate=1000000')

    print("\n=== QoS Network Ready ===")
    print("h1 (10.0.0.1) - VoIP    - Queue 0 (High)")
    print("h2 (10.0.0.2) - HTTP    - Queue 1 (Medium)")
    print("h3 (10.0.0.3) - FTP     - Queue 2 (Low)")
    print("========================\n")

    CLI(net)
    net.stop()

if __name__ == '__main__':
    run()
