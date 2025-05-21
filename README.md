# Vast Grafana Dashboards

# Introduction
VAST versions 4.7 and later have built-in Prometheus exporters for easy integration into existing monitoring infrastructure.

Here you can find dashboards that provide statistics and visualisations based on scraped metrics: 

* Main dashboard - Cluster health and statistics
* Capacity Utilization 
* CNodes
* DNodes, SSDs and NVRAMs
* Protocols metadata statistics - NFSv3, NFSv4 and S3 metadata latency statistics
* Replication streams (supported on versions 5.2 and later)
* Performance per vip, vippool, user and view
* Performance per tenant (supported on versions 5.3 and later)
* Alarms
Navigation between the dashboards is done through the "Switch Dashboard" button located at the right top corner of every dashboard.

## Compatibility
Those dashboards support VAST 4.7 and later with the built-in Prometheus exporter. For a 4.6 dashboard, please contact VAST support.

Please note that the current version of the dashboard use prominent metrics that are currently on our external exporter only. We will include those metrics in the internal (built in) exporter in the next SP of version 5.0.

Therefore, we recommend using vast external exporter for this version of the dashboards. You may find some instructions on how to configure the exporter [here](https://github.com/vast-data/vast-exporter).

If you have any troubles configuring the external exporter, please contact VAST support.

The dashboards are .json files - please import them to your Grafana instance, and configure a Prometheus data source, as explained in the following paragraph.

<br>

# Prometheus Configuration
## External Exporter
Here's an example 'prometheus.yml' configuration using an external exporter.

```yaml
# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: "vast"

    # metrics_path defaults to '/metrics'
    # scheme defaults to 'http'.
    scrape_interval: 1m
    scrape_timeout: 50s
    
    static_configs:
      - targets: ["<EXPORTER HOST>:8000"]
```
<br>

## Internal (Built-In) Exporter
VAST clusters running 4.7 and later provide separate metrics endpoints to give more control on which metrics to fetch and how often to fetch them. This allows users to customize the trade off between metric freshness and the cost of fetching the data.

Here's an example `prometheus.yml` configuration for the 4 endpoints used by those dashboards with some guidelines on scraping intervals.

```yaml
  # Base metrics contain key cluster and protocol stats
  # Recommended scrape interval is >= 30s
  - job_name: 'vast_base'
    metrics_path: '/api/prometheusmetrics/'
    scrape_interval: 30s
    scrape_timeout: 20s

    scheme: https
    static_configs:
      - targets: ['10.71.10.202:443']
    tls_config:
        insecure_skip_verify: true

    basic_auth:
       username: 'admin'
       password: 'xxxxxx'


  # Device metrics can be data intensive for larger clusters
  # Recommended scrape interval is >= 60s
  - job_name: 'vast_devices'
    metrics_path: '/api/prometheusmetrics/devices'
    scrape_interval: 60s
    scrape_timeout: 45s

    scheme: https
    static_configs:
      - targets: ['10.71.10.202:443']
    tls_config:
        insecure_skip_verify: true

    basic_auth:
       username: 'admin'
       password: 'xxxxxx'


  # View metrics can be data intensive for clusters with many views
  # Recommended scrape interval is >= 60s
  - job_name: 'vast_views'
    metrics_path: '/api/prometheusmetrics/views'
    scrape_interval: 120s
    scrape_timeout: 60s

    scheme: https
    static_configs:
      - targets: ['10.71.10.202:443']
    tls_config:
        insecure_skip_verify: true

    basic_auth:
       username: 'admin'
       password: 'xxxxxx'


  # User metrics can be data intensive for clusters with many users
  # Recommended scrape interval is >= 60s
  - job_name: 'vast_users'
    metrics_path: '/api/prometheusmetrics/users'
    scrape_interval: 120s
    scrape_timeout: 60s

    scheme: https
    static_configs:
      - targets: ['10.71.10.202:443']
    tls_config:
        insecure_skip_verify: true

    basic_auth:
       username: 'admin'
       password: 'xxxxxx'
```
