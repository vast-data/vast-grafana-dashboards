from prometheus_client import start_http_server, Gauge
import time
import warnings
import pexpect
import re
import ast
from concurrent.futures import ThreadPoolExecutor
import argparse
import sys
import json
import humanfriendly
import subprocess
from datetime import datetime
from vastpy import VASTClient

warnings.filterwarnings("ignore")


parser = argparse.ArgumentParser(description="Parser for Linux Cumulus switches - OS 5.11 and later. Parses QoS and BW statistics")
parser.add_argument("--switch_username", type=str, help="Username for Cumulus Linux switches")
parser.add_argument("--switch_password", type=str, help="Password for Cumulus Linux switches")
parser.add_argument("--address", type=str, help="Cluster VMS IP Address")
parser.add_argument("--vms_username", type=str, help="Cluster username - could be read only")
parser.add_argument("--vms_password", type=str, help="Cluster password")
parser.add_argument("--port", type=int, default=8007, help="Bind port for Promethehus")

args = parser.parse_args()


if not args.switch_username or not args.switch_password or not args.address or not args.vms_username or not args.vms_password:
    print("Error: All of --switch_username, --switch_password, --address, --vms_username and --vms_password are needed")
    parser.print_usage()
    sys.exit(1)


# Class for collecting switch metrics
class SwitchMetricsCollector:
    def __init__(self, switch_ip, hostname, cluster, role):
        self.ip = switch_ip
        self.username = args.switch_username  
        self.password = args.switch_password
        self.hostname = hostname
        self.cluster = cluster
        self.role = role

    def ping_ip(self):
        response = subprocess.run(['ping', '-c', '1', '-W', '2', self.ip],
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL) 
        return response.returncode == 0
    
    #Function to deal with sudo
    def ssh_with_sudo_pexpect(self, child, command):       
        child.sendline(f'sudo {command}')
        i = child.expect([r'[Pp]assword', r'\$'], timeout=None)
        if i == 0: #If password was required
            child.sendline(self.password)
            child.expect(r'\$')
        output = child.before.decode('utf-8')  # Get command output
        return output
    
    def parse_output(self, child, command):
        output = self.ssh_with_sudo_pexpect(child, command)
        output = re.sub(r'\x1b\[.*?[a-zA-Z]', '', output)
        output = list(filter(lambda x: x != '', output.splitlines()))
        return output

    def collect_bw_metrics(self, child, command):
        output = self.ssh_with_sudo_pexpect(child, command)
        bw_data = [x for x in output.splitlines() if 'swp' in x]
        return bw_data

    def collect_arp_violations_data(self, child, command):
        output = self.parse_output(child, command)
        arp_data = json.loads((output[1]))
        return arp_data["13"]

    def collect_vtep_data(self, child, command, internal_ips):
        output = self.parse_output(child, command)
        output = [((line.replace("[remote-vtep]", "")).replace("local-vtep", "")).strip() for line in output if ("[remote-vtep]" in line or "local-vtep" in line)]
        missing = [ip for ip in internal_ips if ip not in output]
        return (output, missing)

    def collect_udev_logs(self, child, command):
        output = self.parse_output(child, command)
        times = [line.split(" ")[0] for line in output if 'sending UDEV event' in line]
        return [(datetime.fromisoformat(timestamp)).timestamp() for timestamp in times]

    def collect_bgp_data(self, child, command, leafs, trunks):
        output = self.parse_output(child, command)
        output = [re.sub(r"\(swp.*", '', line).strip() for line in output if 'swp' in line]
        trunks = [trunk for trunk in trunks if trunk in output]
        leafs = [leaf for leaf in leafs if leaf in output]
        missing_trunks = [trunk for trunk in trunks if trunk not in output]
        missing_leafs = [leaf for leaf in leafs if leaf not in output]
        return (leafs, trunks, missing_leafs, missing_trunks)

    def collect_ntp_data(self, child, command):
        output = self.parse_output(child, command)
        output = [line.split() for line in output if ("===" not in line or (line[6]).isdigit())]
        return output
    
    def connect(self):
        try:
            child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no -o "UserKnownHostsFile /dev/null" {self.username}@{self.ip}')
            i = child.expect([r'[Pp]assword', r'\$'])
            if i == 0:
                child.sendline(self.password)
                child.expect(r'\$')
            return child
        except Exception as e:
            print(f"Failed connecting {collector.ip}: str{e}")


def extract_switch_details():
    client = VASTClient(user=args.vms_username, password=args.vms_password, address=args.address)
    switches = client.switches.get()
    parsed_switches = []
    for switch in switches:
        ip = switch["mgmt_ip"]
        hostname = switch["hostname"]
        cluster = client.clusters.get()[0]["name"]
        role = switch["role"]
        if (switch["switch_type"]).lower() == "cumulus":
            parsed_switches.append(SwitchMetricsCollector(ip, hostname, cluster, role))
    return parsed_switches


# Thread function to collect metrics and update the registry
def connect_to_switch_and_collect_metrics(collector, gauges, leafs, trunks, leaf_loopback_ips):
    try:
        start_time = time.time()
        hostname = collector.hostname
        ip = collector.ip
        cluster = collector.cluster
        role = collector.role
        # Ping switch before ssh
        is_reachable = collector.ping_ip()
        if "switch_reachable" not in gauges:
            gauges['switch_reachable'] = Gauge('switch_reachable', 'Ping switch and check if it is reachable', labelnames=['switch_hostname', 'switch_ip', 'cluster'])
        if is_reachable:
            gauges['switch_reachable'].labels(switch_hostname=hostname, switch_ip=ip, cluster=cluster).set(1)
        else:
            gauges['switch_reachable'].labels(switch_hostname=hostname, switch_ip=ip, cluster=cluster).set(0)
            return None

        child = collector.connect()

        # Update Bandwidth metrics
        try:
            bw_data = collector.collect_bw_metrics(child, "cat /proc/net/dev")
            for line in bw_data:
                parsed_line = line.replace(':', '').split()
                port = parsed_line[0]
                rx_bytes = int(parsed_line[1])
                tx_bytes = int(parsed_line[9])

                if 'rx_bytes' not in gauges:
                    gauges['rx_bytes'] = Gauge('rx_bytes', 'RX Bytes', labelnames=['port', 'switch_hostname', 'switch_ip', 'cluster'])
                if 'tx_bytes' not in gauges:
                    gauges['tx_bytes'] = Gauge('tx_bytes', 'TX Bytes', labelnames=['port', 'switch_hostname', 'switch_ip', 'cluster'])

                gauges['rx_bytes'].labels(port=port, switch_hostname=hostname, switch_ip=ip, cluster=cluster).set(rx_bytes)
                gauges['tx_bytes'].labels(port=port, switch_hostname=hostname, switch_ip=ip, cluster=cluster).set(tx_bytes)
        except Exception as e:
            print(f"Failed collecting Bandwidth metrics for {hostname}: {str(e)}") 

        # Update Logs Metrics    
        try:
            udev_times = collector.collect_udev_logs(child, "grep UDEV /var/log/syslog |grep 'Unregistering from PCI'")
            if 'udev_unregistered_from_pci' not in gauges:
                gauges['udev_unregistered_from_pci'] = Gauge('udev_unregistered_from_pci', 'Unregistered from PCI', labelnames=['event_count', 'switch_hostname', 'switch_ip', 'cluster'])
            for i in range(len(udev_times)):
                gauges['udev_unregistered_from_pci'].labels(event_count=i, switch_hostname=hostname, switch_ip=ip, cluster=cluster).set(udev_times[i])
        except Exception as e:
            print(f"Failed collecting UDEV logs for {hostname}: {str(e)}")

        # Collect VTEP Data if switch is leaf
        if 'leaf' in role.lower():
            try:
                vtep_data = collector.collect_vtep_data(child, "nv show evpn vni 69", leaf_loopback_ips)
                if 'missing_vtep' not in gauges:
                    gauges['missing_vtep'] = Gauge('missing_vtep', "Missing Vtep", labelnames=['switch_hostname', 'switch_ip', 'cluster', 'vtep'])
                for vtep in vtep_data[0]:
                    gauges['missing_vtep'].labels(switch_hostname=hostname, switch_ip=ip, cluster=cluster, vtep=vtep).set(0)
                for vtep in vtep_data[1]:
                    gauges['missing_vtep'].labels(switch_hostname=hostname, switch_ip=ip, cluster=cluster, vtep=vtep).set(1)
            except Exception as e:
                print(f"Failed collecting Vtep data for {hostname}: {str(e)}")

        # Collect BGP Data
        try:
            bgp_data = collector.collect_bgp_data(child, 'sudo vtysh -c "show bgp summary"', leafs, trunks)
            if 'bgp_connection_missing' not in gauges:
                gauges['bgp_connection_missing'] = Gauge('bgp_connection_missing', "Missing BGP Connections", labelnames=['bgp_connection', 'switch_hostname', 'switch_ip', 'cluster'])
            if 'spine' in hostname: # If switch is spine
                for leaf in bgp_data[0]:
                    gauges['bgp_connection_missing'].labels(bgp_connection=leaf, switch_hostname=hostname, switch_ip=ip, cluster=cluster).set(0)
                for leaf in bgp_data[2]:
                    gauges['bgp_connection_missing'].labels(bgp_connection=leaf, switch_hostname=hostname, switch_ip=ip, cluster=cluster).set(1)
            if 'leaf' in hostname: # If switch is leaf
                for trunk in bgp_data[1]:
                    gauges['bgp_connection_missing'].labels(bgp_connection=trunk, switch_hostname=hostname, switch_ip=ip, cluster=cluster).set(0)
                for trunk in bgp_data[3]:
                    gauges['bgp_connection_missing'].labels(bgp_connection=trunk, switch_hostname=hostname,  switch_ip=ip, cluster=cluster).set(1)
        except Exception as e:
            print(f"Failed collecting BGP data for {hostname}: {str(e)}")  

        # Collect ARP Violation Data
        try:
            arp_data = collector.collect_arp_violations_data(child, "sudo /usr/lib/cumulus/mlxcmd --json traps show group-stats")
            if "switch_arp_violations" not in gauges:
                gauges["switch_arp_violations"] = Gauge('switch_arp_violations', "Switch ARP Violations", labelnames=['switch_hostname', 'switch_ip', 'cluster'])
            gauges["switch_arp_violations"].labels(switch_hostname=hostname, switch_ip=ip, cluster=cluster).set(arp_data["violation_counter_pkts"])
        except Exception as e:
            print(f"Failed collecting ARP Violation data for {hostname}: {str(e)}")

        
        # Collect NTP Data
        try:
            ntp_data = collector.collect_ntp_data(child, "ntpq -p")
            if "ntp_server_reachable" not in gauges:
                gauges["ntp_server_reachable"] = Gauge('ntp_server_reachable', "NTP Server Status", labelnames=['ntp_server', 'switch_hostname', 'switch_ip', 'cluster'])
            for server in ntp_data:
                if len(server) >= 7 and server[6].isdigit():
                    gauges["ntp_server_reachable"].labels(switch_hostname=hostname, switch_ip=ip, cluster=cluster, ntp_server=server[0]).set(server[6])
        except Exception as e:
            print(f"Failed collecting NTP data for {hostname}: {str(e)}")
      
            
        # Close SSH session
        child.sendline('exit')
        child.expect(pexpect.EOF)

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time taken to scrape all metrics from {hostname} {elapsed_time:.2f} seconds") # Will be deleted in production 
    
    except Exception as e:
        print(f"Failed connecting to {hostname} or initializing metrics collection: {str(e)}")

def extract_loopback_ips(collector):
    child = collector.connect()
    output = collector.parse_output(child, "nv show interface lo ip add")
    output = (re.match(r"^[^/]+", output[3])).group(0)
    return output

def print_gauges(gauges):
    for key, gauge in gauges.items():
        # Iterate through all the labels and values in the Gauge object
        samples = list(gauge.collect())[0].samples
        for sample in samples:
            print(f"{sample.name} {sample.labels} = {sample.value}")

# Main function
if __name__ == "__main__":

    # Extract switch details
    switches_details = extract_switch_details()
    leafs = [switch.hostname for switch in switches_details if 'leaf' in (switch.role).lower()]
    trunks = [switch.hostname for switch in switches_details if 'spine' in (switch.role).lower()]
    leaf_loopback_ips = [extract_loopback_ips(switch) for switch in switches_details if 'leaf' in (switch.role).lower()]


    # Start Prometheus HTTP server
    start_http_server(args.port)

    # Create a dictionary to hold Prometheus gauges
    gauges = {}

    # Use a ThreadPoolExecutor for multithreading
    with ThreadPoolExecutor(max_workers=len(switches_details)) as executor:
        while True:
            # Submit each switch to be handled by a thread
            futures = [executor.submit(connect_to_switch_and_collect_metrics, switch, gauges, leafs, trunks, leaf_loopback_ips) for switch in switches_details]

            # Wait for all threads to complete
            for future in futures:
                future.result()
            #print_gauges(gauges) # Unhash to print the metrics to the screen
            