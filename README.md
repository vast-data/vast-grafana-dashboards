# Vast Grafana Dashboards

## Introduction

VAST versions 4.7 and later have built-in Prometheus exporters for easy integration into existing monitoring infrastructure.

This repository includes Grafana dashboards that provide statistics and visualizations based on scraped metrics:

* **Main dashboard** – Cluster health and statistics
* **Capacity Utilization**
* **CNodes**
* **DNodes, SSDs and NVRAMs**
* **Protocols metadata statistics** – NFSv3, NFSv4, and S3 metadata latency
* **Replication streams** (requires VAST 5.2 or later)
* **Performance per VIP, VIP pool, user, and view**
* **Performance per tenant** (requires VAST 5.3 or later)
* **Alarms**
* **NICs State**
* **Switches State** (requires NVIDIA Cumulus Linux 5.12.1 or later – see [Switches Monitoring](#switches-monitoring))

### Example from the main dashboard

![Main Dashboard Screenshot](https://github.com/user-attachments/assets/68e5e41a-d39f-4d95-ae58-d919bcd4a33e)

Navigation between the dashboards is done through the buttons located at the top-right corner of every dashboard:

<img width="931" alt="Navigation" src="https://github.com/user-attachments/assets/924df197-3aef-45c3-b625-b1a35226ca73" />

---

## Compatibility

These dashboards support VAST versions 5.1-sp40 and later with the built-in Prometheus exporter. For older versions, please contact VAST support.

The dashboards are provided as `.json` files – import them into your Grafana instance and configure a Prometheus data source as shown below.

---

## Prometheus Configuration

### Internal (Built-In) Exporter

VAST clusters running version 4.7 and later expose separate metrics endpoints, giving control over what metrics to fetch and how frequently.

Example `prometheus.yml` configuration:

```yaml
# Base metrics
- job_name: 'vast_base'
  metrics_path: '/api/prometheusmetrics/'
  scrape_interval: 30s
  scrape_timeout: 20s
  scheme: https
  static_configs:
    - targets: ['<vms_ip>:443']
  tls_config:
    insecure_skip_verify: true
  basic_auth:
    username: 'admin'
    password: 'xxxxxx'

# Device metrics
- job_name: 'vast_devices'
  metrics_path: '/api/prometheusmetrics/devices'
  scrape_interval: 60s
  scrape_timeout: 45s
  scheme: https
  static_configs:
    - targets: ['<vms_ip>:443']
  tls_config:
    insecure_skip_verify: true
  basic_auth:
    username: 'admin'
    password: 'xxxxxx'

# View metrics
- job_name: 'vast_views'
  metrics_path: '/api/prometheusmetrics/views'
  scrape_interval: 120s
  scrape_timeout: 60s
  scheme: https
  static_configs:
    - targets: ['<vms_ip>:443']
  tls_config:
    insecure_skip_verify: true
  basic_auth:
    username: 'admin'
    password: 'xxxxxx'

# User metrics
- job_name: 'vast_users'
  metrics_path: '/api/prometheusmetrics/users'
  scrape_interval: 120s
  scrape_timeout: 60s
  scheme: https
  static_configs:
    - targets: ['<vms_ip>:443']
  tls_config:
    insecure_skip_verify: true
  basic_auth:
    username: 'admin'
    password: 'xxxxxx'
```

### Prometheus Authentication

Prometheus supports both basic authentication and bearer tokens. Example using bearer token:

```yaml
- job_name: 'vast_views'
  scrape_interval: 120s
  scrape_timeout: 90s
  scheme: https
  metrics_path: '/api/prometheusmetrics/views'
  static_configs:
    - targets: ['<vms_ip>:443']
  authorization:
    type: Bearer
    credentials: '<your-token>'
  tls_config:
    insecure_skip_verify: true
```

---

## Supported Metrics Endpoints

* `/api/prometheusmetrics/alarms` – All active VAST cluster alarms
* `/api/prometheusmetrics/users` – Per-user bandwidth, IOPS, and metadata IOPS
* `/api/prometheusmetrics/views` – Performance per view, logical/physical capacity, QoS
* `/api/prometheusmetrics/quotas` – Quota limits, exceeded/bloacked user counts
* `/api/prometheusmetrics/replications` – Replication stream stats (5.2-sp10+)
* `/api/prometheusmetrics/devices` – SSD/NVRAM state and media info
* `/api/prometheusmetrics/defrag` – Defragmentation metrics
* `/api/prometheusmetrics/vips` – VIP/VIP pool performance
* `/api/prometheusmetrics/user_view` – Per-user + per-view metrics (5.2-sp15+)
* `/api/prometheusmetrics/nics` – NICs state/errors (5.2-sp20+)
* `/api/prometheusmetrics/` – General cluster + CNode metrics
* `/api/prometheusmetrics/all` – All metrics (use cautiously on large clusters)
* `/api/prometheusmetrics/user_connections` - Reports S3 connections per user. Applies only to users with a QoS policy that defines a maximum user connections limit (5.2.2+).
* `/api/prometheusmetrics/kafka_targets` - Metrics per Kafka broker (5.4.1+).

---

## Switches Monitoring

Our monitoring solution supports **NVIDIA Cumulus switches (v5.12.1 and later)**. It includes:

* **OpenTelemetry (OTEL)** – native switch support for metrics
* **Custom Prometheus exporter** – fills gaps until OTEL support is complete

Both components export to Prometheus and are visualized in the **"Switches State"** Grafana dashboard.

📄 For complete setup instructions, see [switch\_monitoring.md](./switches/README.md)
