from pox.core import core
from pox.lib.util import dpid_to_str
import pox.openflow.libopenflow_01 as of
from pox.forwarding.l2_learning import LearningSwitch
import time

log = core.getLogger()
path_log = {}

class PathTracerSwitch(LearningSwitch):
    def __init__(self, connection, transparent=False):
        LearningSwitch.__init__(self, connection, transparent)
        self.dpid = connection.dpid
        log.info("PathTracer switch %s connected", dpid_to_str(self.dpid))

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            return

        ip = packet.find('ipv4')
        if ip:
            key = (str(ip.srcip), str(ip.dstip))
            if key not in path_log:
                path_log[key] = []
            path_log[key].append({
                'switch': dpid_to_str(self.dpid),
                'in_port': event.port,
                'time': time.strftime('%H:%M:%S')
            })
            log.info("*** PATH TRACE [%s -> %s] switch=%s in_port=%s",
                     ip.srcip, ip.dstip, dpid_to_str(self.dpid), event.port)

        # Call parent l2_learning handler to do actual forwarding
        LearningSwitch._handle_PacketIn(self, event)

def _handle_ConnectionUp(event):
    log.info("Switch UP: %s", dpid_to_str(event.dpid))
    PathTracerSwitch(event.connection)

def launch(transparent=False):
    log.info("Path Tracer loading...")
    core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp)
    log.info("Path Tracer loaded. Waiting for switches...")
