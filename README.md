# Vast Grafana Dashboards

# Introduction
VAST versions 4.7 and later have built-in Prometheus exporters for easy integration into existing monitoring infrastructure.

Here you may find dashboards that provide statistics and visualisations based on scraped metrics: 

* Main dashboard - Cluster health and statistics
* Capacity Utilization 
* CNodes
* DNodes, SSDs and NVRAMs
* Protocols metadata statistics - NFSv3, NFSv4 and S3 metadata latency statistics
* Replication streams (supported on versions 5.2 and later)
* Performance per vip, vippool, user and view
* Performance per tenant (supported on versions 5.3 and later)
* Alarms

Navigation between the dashboards is done through the buttons located at the right top corner of every dashboard -

![image](https://github.com/user-attachments/assets/24359e57-a056-4f91-a737-bcbde60f9f59)


## Compatibility
Those dashboards support VAST 5.1-sp40 and later with the built-in Prometheus exporter. For older versions, please contact VAST support.

The dashboards are .json files - please import them to your Grafana instance, and configure a Prometheus data source, as explained in the following paragraph.

<br>

# Prometheus Configuration
## Internal (Built-In) Exporter
VAST clusters running 4.7 and later provide separate metrics endpoints to give more control on which metrics to fetch and how often to fetch them. This allows users to customize the trade off between metric freshness and the cost of fetching the data.

Here's an example `prometheus.yml` configuration for 4 endpoints used by those dashboards with some guidelines on scraping intervals.

```yaml
  # Base metrics contain key cluster and protocol stats
  # Recommended scrape interval is >= 30s
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


  # Device metrics can be data intensive for larger clusters
  # Recommended scrape interval is >= 60s
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


  # View metrics can be data intensive for clusters with many views
  # Recommended scrape interval is >= 60s
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


  # User metrics can be data intensive for clusters with many users
  # Recommended scrape interval is >= 60s
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
Prometheus supports basic authentication and bearer token authentication. 
An example for authentication with bearer token -

```yaml
scrape_configs:
  - job_name: 'vast_views'
    scrape_interval: 120s
    scrape_timeout: 90s
    scheme: https
    metrics_path: '/api/prometheusmetrics/views'
    static_configs:
      - targets: ['<vms_ip>:443>']
    authorization:
      type: Bearer
      credentials: '<your-token>'
    tls_config:
      insecure_skip_verify: true
```
### Supported Metrics Endpoints
`/api/prometheusmetrics/alarms` - Exports all active VAST cluster alarms.
`/api/prometheusmetrics/users` - Exports user bandwidth, IOPS and metadata IOPS metrics on read and/or write operations.
`/api/prometheusmetrics/views` - Exports performance metrics per view, including bandwidth, IOPS, metadata IOPS, latency and QoS, and also view logical and physical capacity.
`/api/prometheusmetrics/quotas` - Provides information related to quotas configured on the cluster, such as the quota limits set and number of users who have exceeded the quota or who have been blocked due to quota exceeded condition.
`/api/prometheusmetrics/replications` - Provides information related to replication streams - Replication stream state, RPO and RPO offset, bandwidth, logical and physical backlog. Supported on versions 5.2-sp10 and later.
`/api/prometheusmetrics/devices` - Provides information about the SSD or NVRAM physical state, such as presence of media errors or current temperature, and overall operational status (active or failed).
`/api/prometheusmetrics/defrag` - Exports metrics related to defragmentation.
`/api/prometheusmetrics/vips` - Exports vip / vipool performance metrics, including a metric that provides mapping of CNode, vip and vippool.
`/api/prometheusmetrics/user_view` - Exports performance metrics per user and view. Supported on version 5.2-sp15 and later.
`/api/prometheusmetrics/nics` - Provides information on NICs state and errors (for example - out of sequence, out of buffers and symbol errors).
`/api/prometheusmetrics/` - Exports cluster and CNode metrics that are not exported by the above-listed endpoints. This includes, for example, performance metrics per storage protocol.
`/api/prometheusmetrics/all` - Exports all VAST Cluster metrics. This includes each and every metrics that can be exported by the above-listed exporter endpoints. Due to big amount of data being exported, using this endpoint to collect metrics from a large cluster is not recommended.
``



