"""
SDN Path Tracing Tool - POX Controller Component
Tracks flow rules, identifies forwarding paths, and logs packet routes.
"""

from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ipv4 import ipv4
from pox.lib.addresses import EthAddr, IPAddr
import time

log = core.getLogger()

# ─────────────────────────────────────────────
# Global path log: stores every forwarding decision
# Format: { (src_ip, dst_ip): [(dpid, in_port, out_port, timestamp), ...] }
# ─────────────────────────────────────────────
path_log = {}

# MAC table per switch: { dpid: { mac: port } }
mac_table = {}


class PathTracer(object):
    """
    Handles one OpenFlow switch connection.
    Installs flow rules and records the forwarding path.
    """

    def __init__(self, connection):
        self.connection = connection
        self.dpid = connection.dpid
        mac_table[self.dpid] = {}

        # Listen to PacketIn events on this switch
        connection.addListeners(self)
        log.info("Switch %s connected", dpid_to_str(self.dpid))

    # ── Utility: install a proactive flow rule ──────────────────────────────
    def install_flow(self, match, out_port, idle_timeout=20, hard_timeout=60, priority=100):
        msg = of.ofp_flow_mod()
        msg.match = match
        msg.idle_timeout = idle_timeout
        msg.hard_timeout = hard_timeout
        msg.priority = priority
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)
        log.debug("  [%s] Flow installed: %s → port %s",
                  dpid_to_str(self.dpid), match, out_port)

    # ── Utility: send a single packet out a port (reactive forwarding) ──────
    def send_packet(self, buffer_id, raw_data, out_port, in_port):
        msg = of.ofp_packet_out()
        msg.in_port = in_port
        msg.buffer_id = buffer_id
        if raw_data is not None:
            msg.data = raw_data
        msg.actions.append(of.ofp_action_output(port=out_port))
        self.connection.send(msg)

    # ── Core: handle every PacketIn event ───────────────────────────────────
    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            log.warning("Ignoring incomplete packet")
            return

        dpid = event.dpid
        in_port = event.port

        # ── Step 1: Learn the source MAC ────────────────────────────────────
        src_mac = packet.src
        mac_table[dpid][src_mac] = in_port
        log.info("[%s] Learned %s on port %s",
                 dpid_to_str(dpid), src_mac, in_port)

        # ── Step 2: Path tracing — record IP-level flow ──────────────────────
        ip_pkt = packet.find('ipv4')
        if ip_pkt:
            src_ip = str(ip_pkt.srcip)
            dst_ip = str(ip_pkt.dstip)
            flow_key = (src_ip, dst_ip)

            if flow_key not in path_log:
                path_log[flow_key] = []

            path_log[flow_key].append({
                'switch': dpid_to_str(dpid),
                'in_port': in_port,
                'timestamp': time.strftime('%H:%M:%S')
            })

            log.info("  PATH TRACE [%s → %s] via switch %s in_port=%s",
                     src_ip, dst_ip, dpid_to_str(dpid), in_port)

        # ── Step 3: Decide output port ───────────────────────────────────────
        dst_mac = packet.dst
        if dst_mac in mac_table[dpid]:
            out_port = mac_table[dpid][dst_mac]
            log.info("  [%s] Known destination %s → port %s",
                     dpid_to_str(dpid), dst_mac, out_port)

            # Install a flow rule so future packets skip the controller
            match = of.ofp_match.from_packet(packet, in_port)
            self.install_flow(match, out_port)

        else:
            # Unknown destination: flood
            out_port = of.OFPP_FLOOD
            log.info("  [%s] Unknown destination %s → FLOOD",
                     dpid_to_str(dpid), dst_mac)

        # ── Step 4: Record out_port in path log ──────────────────────────────
        if ip_pkt and path_log.get((str(ip_pkt.srcip), str(ip_pkt.dstip))):
            path_log[(str(ip_pkt.srcip), str(ip_pkt.dstip))][-1]['out_port'] = out_port

        # ── Step 5: Send the packet ──────────────────────────────────────────
        self.send_packet(event.ofp.buffer_id,
                         event.data if event.ofp.buffer_id == 0xFFFFFFFF else None,
                         out_port, in_port)


# ─────────────────────────────────────────────
# PathTracerLauncher: registered as a POX component
# ─────────────────────────────────────────────
class PathTracerLauncher(object):
    def __init__(self):
        log.info("Path Tracer Controller starting...")
        core.openflow.addListeners(self)

    def _handle_ConnectionUp(self, event):
        PathTracer(event.connection)

    def _handle_ConnectionDown(self, event):
        log.info("Switch %s disconnected", dpid_to_str(event.dpid))
        # Print path summary when switch disconnects
        self._print_path_summary()

    def _print_path_summary(self):
        log.info("\n===== FORWARDING PATH SUMMARY =====")
        if not path_log:
            log.info("No paths recorded.")
            return
        for (src, dst), hops in path_log.items():
            log.info("Flow: %s → %s", src, dst)
            for i, hop in enumerate(hops):
                log.info("  Hop %d: switch=%s  in_port=%s  out_port=%s  time=%s",
                         i + 1,
                         hop.get('switch'),
                         hop.get('in_port'),
                         hop.get('out_port', '?'),
                         hop.get('timestamp'))
        log.info("===================================\n")


def launch():
    """Entry point called by POX."""
    core.registerNew(PathTracerLauncher)
    log.info("Path Tracer loaded. Waiting for switches...")
