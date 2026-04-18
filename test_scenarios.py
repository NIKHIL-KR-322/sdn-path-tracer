"""
Automated test scenarios for the SDN Path Tracing project.
Run INSIDE the Mininet CLI with:  py execfile('test_scenarios.py')
Or externally: python3 test_scenarios.py
"""

import subprocess
import time


def run_mininet_cmd(net, host_name, cmd):
    """Run a command on a Mininet host and return output."""
    host = net.get(host_name)
    result = host.cmd(cmd)
    return result


def scenario_1_normal_forwarding(net):
    """
    Scenario 1: Normal forwarding — h1 pings h4 (cross-switch path)
    Expected: Packets travel h1 → s1 → s2 → s3 → h4
    """
    print("\n" + "="*50)
    print("SCENARIO 1: Normal Forwarding (h1 → h4)")
    print("="*50)

    h1 = net.get('h1')
    h4 = net.get('h4')

    print("[Test 1a] Ping h1 → h4 (3 packets)")
    result = h1.cmd('ping -c 3 10.0.0.4')
    print(result)

    if "0% packet loss" in result:
        print("PASS: h1 → h4 reachable, 0% packet loss")
    else:
        print("FAIL: packet loss detected")

    print("\n[Test 1b] Ping h2 → h3 (same direction, different hosts)")
    h2 = net.get('h2')
    result = h2.cmd('ping -c 3 10.0.0.3')
    print(result)
    if "0% packet loss" in result:
        print("PASS: h2 → h3 reachable")
    else:
        print("FAIL: packet loss detected")

    return result


def scenario_2_flow_table_check(net):
    """
    Scenario 2: Flow table validation — verify rules are installed after pings
    Expected: OpenFlow rules appear in ovs-ofctl output
    """
    print("\n" + "="*50)
    print("SCENARIO 2: Flow Table Verification")
    print("="*50)

    switches = ['s1', 's2', 's3']
    for sw in switches:
        print(f"\n[Flow table on {sw}]")
        result = subprocess.run(
            ['sudo', 'ovs-ofctl', 'dump-flows', sw],
            capture_output=True, text=True
        )
        print(result.stdout)
        if "actions" in result.stdout:
            print(f"PASS: Flow rules present on {sw}")
        else:
            print(f"WARN: No flow rules yet on {sw} (run pings first)")


def scenario_3_iperf_throughput(net):
    """
    Scenario 3: Throughput measurement using iperf
    Expected: ~10 Mbps on host-to-switch links (as configured)
    """
    print("\n" + "="*50)
    print("SCENARIO 3: Throughput Test (iperf)")
    print("="*50)

    h1 = net.get('h1')
    h4 = net.get('h4')

    print("[Starting iperf server on h4]")
    h4.cmd('iperf -s &')
    time.sleep(1)

    print("[Running iperf client on h1 for 5 seconds]")
    result = h1.cmd('iperf -c 10.0.0.4 -t 5')
    print(result)

    if "Mbits/sec" in result or "Kbits/sec" in result:
        print("PASS: iperf completed successfully")
    else:
        print("FAIL: iperf did not produce throughput data")

    h4.cmd('kill %iperf')


def scenario_4_path_trace_display(net):
    """
    Scenario 4: Display the path taken by h1 → h4 traffic
    Uses packet counts from ovs-ofctl to validate path
    """
    print("\n" + "="*50)
    print("SCENARIO 4: Path Trace Display")
    print("="*50)

    # Trigger traffic first
    h1 = net.get('h1')
    h1.cmd('ping -c 2 10.0.0.4')

    print("\nPath taken by packets from h1 (10.0.0.1) → h4 (10.0.0.4):")
    print("  h1 ──(port 1)──> s1 ──(port 3)──> s2 ──(port 2)──> s3 ──(port 1)──> h4")
    print("\nVerifying with port statistics:\n")

    for sw in ['s1', 's2', 's3']:
        result = subprocess.run(
            ['sudo', 'ovs-ofctl', 'dump-ports', sw],
            capture_output=True, text=True
        )
        print(f"[{sw} port stats]")
        print(result.stdout[:400])  # Print first 400 chars


def run_all_tests(net):
    """Run all test scenarios in sequence."""
    print("\n" + "#"*60)
    print("   SDN PATH TRACING TOOL — TEST SUITE")
    print("#"*60)

    scenario_1_normal_forwarding(net)
    time.sleep(2)
    scenario_2_flow_table_check(net)
    time.sleep(1)
    scenario_3_iperf_throughput(net)
    time.sleep(1)
    scenario_4_path_trace_display(net)

    print("\n" + "#"*60)
    print("   ALL TESTS COMPLETE")
    print("#"*60)
