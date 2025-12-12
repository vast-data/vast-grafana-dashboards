# Monitoring Cumulus Switches (v5.12+)

This document explains how to set up monitoring for Cumulus Linux switches version 5.12 and later using **OpenTelemetry (OTEL)** and a **custom Prometheus exporter**. Metrics are visualized in Grafana dashboards for daily monitoring.

## <span style="color:red;">Update Dec 2025 - Please do not use monitoring on Cumulus switches of versions 5.13 and 5.14, due to Nvidia bug #4641291, solved in Cumulus 5.15</span>

---

## Contents

* [OTEL Monitoring Setup](#otel-monitoring-setup)

  - [Clush Configuration](#clush-configuration)
  - [OTEL Collector Configuration (Server-Side)](#otel-collector-configuration-server-side)
  - [Switch-Side OTEL Configuration](#switch-side-otel-configuration)
* [Prometheus Exporter Setup](#prometheus-exporter-setup)

  - [Prometheus Configuration](#prometheus-configuration)
  - [Custom Exporter Script](#custom-exporter-script)
* [Grafana Dashboard Guidelines](#grafana-dashboard-guidelines)

---

## OTEL Monitoring Setup

### Clush Configuration

Ensure `clush` (from `clustershell`) is installed on a cluster node. Then edit `/etc/clustershell/groups.d/local.cfg`, for example:

```ini
spines: 10.1.2.[100-110]
leaves1: 10.1.3.[100-110]
leaves2: 10.1.4.[100-110]
switches: @spines,@leaves1,@leaves2
```

Generate an SSH key and copy it to the switches, for example:

```bash
ssh-keygen -t rsa -C "CommentForKey" -b 4096

for i in {100..110}; do
  sshpass -p <cumulus_switch_password> ssh-copy-id -o "StrictHostKeyChecking=no" cumulus@10.1.2.$i
  sshpass -p <cumulus_switch_password> ssh-copy-id -o "StrictHostKeyChecking=no" cumulus@10.1.3.$i
  sshpass -p <cumulus_switch_password> ssh-copy-id -o "StrictHostKeyChecking=no" cumulus@10.1.4.$i
done
```

---

### OTEL Collector Configuration (Server-Side)

1. Open port `4317` (gRPC) on your firewall.
2. Create the file `/path/to/otel/directory/otel-collector-config.yml`:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: "0.0.0.0:4317"
        tls:
          cert_file: /etc/otel/server.crt
          key_file: /etc/otel/server.key

processors:
  resource:
    attributes:
      - key: switch_hostname
        action: insert
        value: "unknown"
      - key: switch_ip
        action: insert
        value: "0.0.0.0"
      - key: cluster
        action: insert
        value: "missing"

exporters:
  prometheus:
    endpoint: "0.0.0.0:9464"
    resource_to_telemetry_conversion:
      enabled: true

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [resource]
      exporters: [prometheus]
```

> **Notes:**
>
> * `resource_to_telemetry_conversion` exports OTEL labels (e.g. `switch_hostname`, `switch_ip`, `cluster`) to Prometheus.
> * Place your TLS `.crt` and `.key` files in the mapped directory.

3. Run the collector:

```bash
docker run -d --name otel-collector \
  -v /path/to/otel/directory/:/etc/otel/ \
  -p 4317:4317 -p 9464:9464 \
  otel/opentelemetry-collector:latest \
  --config=/etc/otel/otel-collector-config.yml
```

---

### Switch-Side OTEL Configuration

Use `clush` to configure all switches:

## For Cumulus 5.12:

```bash
clush -g switches -l cumulus -o "-q" 'nv unset system telemetry'
clush -g switches -l cumulus -o "-q" 'nv action import system security ca-certificate tls-cert data """<public-key-data>"""'
clush -g switches -l cumulus -o "-q" "nv set system telemetry enable on"
clush -g switches -l cumulus -o "-q" "nv set system telemetry export otlp state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats sample-interval 30"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats ingress-buffer priority-group 0"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats ingress-buffer priority-group 1"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats egress-buffer traffic-class 3"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats switch-priority 3"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats class phy state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry buffer-stats export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry histogram export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry control-plane-stats export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry control-plane-stats sample-interval 30"
clush -g switches -l cumulus -o "-q" "nv set system telemetry export otlp grpc cert-id tls-cert"
clush -g switches -l cumulus -o "-q" "nv set system telemetry export otlp grpc destination <host_ip> port 4317"
clush -g switches -l cumulus -o "-q" "nv set system telemetry export vrf mgmt"
clush -g switches -l cumulus -o "-q" "nv set system telemetry label \"switch_ip\" description \"\$(hostname -I | awk '{print \$1}')\""
clush -g switches -l cumulus -o "-q" "nv set system telemetry label \"switch_hostname\" description \"\$(hostname)\""
clush -g switches -l cumulus -o "-q" "nv set system telemetry label cluster description <cluster_name>"
clush -g switches -l cumulus -o "-q" "nv config apply" --assume-yes
```
## For Cumulus 5.15+:

```bash
clush -g switches -l cumulus -o "-q" 'nv unset system telemetry'
clush -g switches -l cumulus -o "-q" 'nv action import system security ca-certificate tls-cert data """<public-key-data>"""'
clush -g switches -l cumulus -o "-q" "nv set system telemetry state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry export otlp state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats sample-interval 30"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats ingress-buffer priority-group 0"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats ingress-buffer priority-group 1"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats egress-buffer traffic-class 3"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats switch-priority 3"
clush -g switches -l cumulus -o "-q" "nv set system telemetry interface-stats class phy state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry buffer-stats export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry histogram export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry control-plane-stats export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry control-plane-stats sample-interval 30"
clush -g switches -l cumulus -o "-q" "nv set system telemetry router export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry router bgp export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry router sample-interval 30"
clush -g switches -l cumulus -o "-q" "nv set system telemetry platform-stats export state enabled"
clush -g switches -l cumulus -o "-q" "nv set system telemetry platform-stats class memory sample-interval 30"
clush -g switches -l cumulus -o "-q" "nv set system telemetry export otlp grpc cert-id tls-cert"
clush -g switches -l cumulus -o "-q" "nv set system telemetry export otlp grpc destination <host_ip> port 4317" # Change to your listening port
clush -g switches -l cumulus -o "-q" "nv set system telemetry export vrf mgmt"
clush -g switches -l cumulus -o "-q" "nv set system telemetry label \"switch_ip\" description \"\$(hostname -I | awk '{print \$1}')\""
clush -g switches -l cumulus -o "-q" "nv set system telemetry label \"switch_hostname\" description \"\$(hostname)\""
clush -g switches -l cumulus -o "-q" "nv set system telemetry label cluster description <cluster_name>"
clush -g switches -l cumulus -o "-q" "nv config apply" --assume-yes
```

> **Notes:**
>
> * Replace `<public-key-data>` with the actual key data.
> * To skip TLS, skip line `nv action import system security ca-certificate tls-cert data """<public-key-data>"""`, and use `nv set system telemetry export otlp grpc insecure enabled` instead of `nv set system telemetry export otlp grpc cert-id tls-cert`.
> * Replace `<host_ip>` and `<cluster_name>` accordingly.

---

## Prometheus Exporter Setup

### Prometheus Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'switch-otel'
    scrape_interval: 15s
    scrape_timeout: 15s
    static_configs:
      - targets: ['<exporter_ip>:9464']
```

Replace `<exporter_ip>` with your OTEL server/exporter IP.

---

### Custom Exporter Script

`scripts/switch_metrics.py` is a Prometheus exporter for metrics not yet exposed via OTEL (e.g., UDEV, NTP).

> **Important:**
>
> * VMS must be online for initial data gathering.
> * Switches must be registered in VMS with the `role` attribute (spine/leaf).
> * The username for all switches must be identical, as well as the password. 

#### Example using `vastpy`:

```python
from vastpy import VASTClient
client = VASTClient(user="<vms-username>", password="<vms-password>", address="<vms-ip>")
client.switches.post(ip="<switch-ip>", username="<switch-username>", password="<switch-password>", role="spine")
```

#### Run the script:

```bash
python switch_metrics.py \
  --switch_username=<switch-username> \
  --switch_password=<switch-password> \
  --address=<vms-ip> \
  --vms_username=<vms-username> \
  --vms_password=<vms-password> \
  --port=8007 # Or another port
```

* Requires **Python 3.9+**
* Requires the following Python packages:

  * `vastpy`
  * `prometheus_client`
  * `pexpect`
  * `humanfriendly`

#### Prometheus Config Addition:

```yaml
- job_name: 'switch'
  scrape_interval: 30s
  scrape_timeout: 30s
  static_configs:
    - targets: ['localhost:8007']
```

---

## Grafana Dashboard Guidelines

At the end of this setup, metrics from both OTEL and the custom exporter should be visible in Grafana.

Refer to the provided dashboards for:

* QoS statistics
* Buffer and interface utilization
* Control-plane statistics
* System status indicators

Each dashboard includes threshold color-coding to highlight alerts or critical states.

---
