## TERMINAL 3 — Run this to create README:

```bash
cat > ~/sdn_path_tracer/README.md << 'EOF'
# SDN Path Tracing Tool
## Using Mininet + POX Controller

---

## Problem Statement

This project implements an SDN-based Path Tracing Tool using Mininet and the POX
OpenFlow controller. The tool identifies and displays the path taken by packets
across a multi-switch network, tracks flow rules, identifies the forwarding path,
displays the route hop-by-hop, and validates using real network tests.

---

## Topology Design

```
H1 (10.0.0.1) ──┐
                 ├── S1 ── S2 ── S3 ──┬── H3 (10.0.0.3)
H2 (10.0.0.2) ──┘                     └── H4 (10.0.0.4)
```

- 4 Hosts: h1, h2, h3, h4
- 3 Switches: s1, s2, s3 (linear chain)
- 1 Remote Controller: POX at 127.0.0.1:6633
- Protocol: OpenFlow 1.0

---

## How It Works

### SDN Controller Logic (path_tracer.py)

The POX controller extends the built-in LearningSwitch class and adds
path tracing on top of it.

1. When a packet arrives at a switch, a PacketIn event is triggered
2. The controller logs the switch DPID and input port — this is the PATH TRACE
3. The LearningSwitch logic learns the source MAC address and maps it to the port
4. If the destination MAC is known, a flow rule is installed on the switch
5. If the destination MAC is unknown, the packet is flooded to all ports
6. After the first packet, all future packets use the installed flow rule
   and bypass the controller completely

### Path Tracing

Every time a PacketIn arrives from an IP packet, the controller logs:
- Which switch received it
- Which port it came in on
- The source and destination IP
- The timestamp

By reading these logs across all 3 switches, the complete hop-by-hop
path of every flow is visible.

### Flow Rules

Flow rules are installed with:
- idle_timeout = 10 seconds
- hard_timeout = 30 seconds
- priority = 65535 (highest)
- match = exact 5-tuple (src/dst IP, src/dst MAC, protocol)
- action = output to specific port

---

## Project Files

| File | Purpose |
|------|---------|
| path_tracer.py | POX controller with path tracing logic |
| topology.py | Custom Mininet topology (4 hosts, 3 switches) |
| README.md | Documentation |

---

## Setup and Installation

### Step 1 — Install dependencies
```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch git python3
```

### Step 2 — Install POX controller
```bash
cd ~
git clone https://github.com/noxrepo/pox
```

### Step 3 — Copy controller to POX
```bash
cp ~/sdn_path_tracer/path_tracer.py ~/pox/ext/path_tracer.py
```

---

## Running the Project

### Always start POX FIRST, then Mininet.

### Terminal 1 — Start POX Controller
```bash
sudo fuser -k 6633/tcp
cd ~/pox
python3 pox.py log.level --DEBUG path_tracer
```

Wait until you see:
```
INFO:path_tracer:Path Tracer loaded. Waiting for switches...
DEBUG:openflow.of_01:Listening on 0.0.0.0:6633
```

### Terminal 2 — Start Mininet Topology
```bash
sudo mn -c
sudo python3 ~/sdn_path_tracer/topology.py
```

You will see all 3 switches connect in Terminal 1:
```
INFO:path_tracer:Switch UP: 00-00-00-00-00-01
INFO:path_tracer:Switch UP: 00-00-00-00-00-02
INFO:path_tracer:Switch UP: 00-00-00-00-00-03
```

---

## Test Scenarios

### Scenario 1 — Basic Connectivity (pingall)
```
mininet> pingall
```
Expected result:
```
h1 -> h2 h3 h4
h2 -> h1 h3 h4
h3 -> h1 h2 h4
h4 -> h1 h2 h3
*** Results: 0% dropped (12/12 received)
```

### Scenario 2 — Cross-Switch Path Trace (h1 to h4)
```
mininet> h1 ping -c 5 10.0.0.4
```
Expected result:
```
5 packets transmitted, 5 received, 0% packet loss
```
In Terminal 1 (POX) you will see:
```
PATH TRACE [10.0.0.1->10.0.0.4] sw=00-00-00-00-00-01 port=1
PATH TRACE [10.0.0.1->10.0.0.4] sw=00-00-00-00-00-02 port=1
PATH TRACE [10.0.0.1->10.0.0.4] sw=00-00-00-00-00-03 port=2
```
This shows the exact hop-by-hop path:
```
h1 → S1(port1→port3) → S2(port1→port2) → S3(port1→port2) → h4
```

### Scenario 3 — Flow Table Verification
```
mininet> h1 ping -c 1 10.0.0.4
mininet> sh ovs-ofctl dump-flows s1
mininet> sh ovs-ofctl dump-flows s2
mininet> sh ovs-ofctl dump-flows s3
```
Expected result: Flow rules with match+action visible on each switch.

### Scenario 4 — Throughput Test (iperf)
```
mininet> h4 iperf -s &
mininet> h1 iperf -c 10.0.0.4 -t 5
```
Expected result:
```
[  1] 0.0-5.0 sec   XX GBytes   XX Gbits/sec
```

### Scenario 5 — Port Statistics (Path Proof)
```
mininet> sh ovs-ofctl dump-ports s1
mininet> sh ovs-ofctl dump-ports s2
mininet> sh ovs-ofctl dump-ports s3
```
High packet counts on specific ports prove the forwarding path.

---

## Expected Output Summary

| Test | Expected Result |
|------|----------------|
| pingall | 0% dropped, 12/12 received |
| h1 ping h4 | 0% packet loss, <60ms first ping |
| dump-flows s1 | Flow rules with actions=output visible |
| iperf h1 to h4 | Several Gbits/sec throughput |
| POX PATH TRACE logs | 3 hops visible across s1, s2, s3 |

---

## Key SDN Concepts Demonstrated

- PacketIn events: Triggered when switch has no flow rule for a packet
- MAC Learning: Controller learns which port each MAC address is on
- Flow Installation: Controller installs rules so future packets bypass controller
- Path Tracing: Logging PacketIn events across switches reveals the full path
- OpenFlow match+action: Exact match on 5-tuple, action is output port

---

## Cleanup
```bash
mininet> exit
sudo mn -c
```

---

## References

1. Mininet: https://mininet.org
2. POX Controller: https://github.com/noxrepo/pox
3. OpenFlow 1.0 Specification: https://opennetworking.org
4. Mininet Walkthrough: https://mininet.org/walkthrough/
5. POX Documentation: https://noxrepo.github.io/pox-doc/html/

EOF
```

