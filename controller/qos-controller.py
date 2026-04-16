from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp

class QoSController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(QoSController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Default flow — send unknown packets to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.logger.info("Switch connected: %s", datapath.id)

    def add_flow(self, datapath, priority, match, actions, queue_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if queue_id is not None:
            actions = [parser.OFPActionSetQueue(queue_id)] + actions

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        # Classify traffic and assign queue
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            udp_pkt = pkt.get_protocol(udp.udp)
            tcp_pkt = pkt.get_protocol(tcp.tcp)

            if udp_pkt:
                # VoIP/UDP → highest priority queue 0
                queue_id = 0
                priority = 30
                match = parser.OFPMatch(in_port=in_port, eth_type=0x0800,
                                        ip_proto=17)
                self.logger.info("VoIP (UDP) flow: %s → %s | Queue 0", src, dst)

            elif tcp_pkt and tcp_pkt.dst_port == 80:
                # HTTP → medium priority queue 1
                queue_id = 1
                priority = 20
                match = parser.OFPMatch(in_port=in_port, eth_type=0x0800,
                                        ip_proto=6, tcp_dst=80)
                self.logger.info("HTTP flow: %s → %s | Queue 1", src, dst)

            elif tcp_pkt and tcp_pkt.dst_port == 21:
                # FTP → lowest priority queue 2
                queue_id = 2
                priority = 10
                match = parser.OFPMatch(in_port=in_port, eth_type=0x0800,
                                        ip_proto=6, tcp_dst=21)
                self.logger.info("FTP flow: %s → %s | Queue 2", src, dst)

            else:
                queue_id = 1
                priority = 5
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst)

            if out_port != ofproto.OFPP_FLOOD:
                self.add_flow(datapath, priority, match, actions, queue_id)

        # Send packet
        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id,
                                  in_port=in_port,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)