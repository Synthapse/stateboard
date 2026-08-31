export type ResourceExplain = {
  label: string;
  does: string;
  usedFor: string;
};

/** Quick explainers for common Terraform resource types. */
const BY_TYPE: Record<string, ResourceExplain> = {
  // —— AWS compute ——
  aws_instance: {
    label: 'EC2 instance',
    does: 'Runs a virtual machine in AWS (CPU, memory, local disk).',
    usedFor: 'App servers, bastion hosts, batch workers, and similar workloads.',
  },
  aws_launch_template: {
    label: 'Launch template',
    does: 'Stores a reusable VM configuration for Auto Scaling / EC2.',
    usedFor: 'Consistent instance setups when scaling fleets.',
  },
  aws_autoscaling_group: {
    label: 'Auto Scaling group',
    does: 'Keeps a pool of EC2 instances at a target size.',
    usedFor: 'Elasticity and replacement of failed app nodes.',
  },
  aws_ecs_service: {
    label: 'ECS service',
    does: 'Keeps container tasks running on ECS.',
    usedFor: 'Long-running microservices and APIs in containers.',
  },
  aws_ecs_cluster: {
    label: 'ECS cluster',
    does: 'Logical grouping of container capacity.',
    usedFor: 'Hosting ECS services and tasks.',
  },
  aws_lambda_function: {
    label: 'Lambda function',
    does: 'Runs code on demand without managing servers.',
    usedFor: 'APIs, event handlers, and short background jobs.',
  },
  aws_eks_cluster: {
    label: 'EKS cluster',
    does: 'Managed Kubernetes control plane in AWS.',
    usedFor: 'Running containerized workloads with Kubernetes.',
  },

  // —— AWS storage ——
  aws_ebs_volume: {
    label: 'EBS volume',
    does: 'Provides durable block storage that attaches to an EC2 instance.',
    usedFor: 'Databases, file systems, and extra disk for VMs.',
  },
  aws_volume_attachment: {
    label: 'Volume attachment',
    does: 'Connects an EBS volume to a specific EC2 instance.',
    usedFor: 'Making block storage available to a VM (no direct cost).',
  },
  aws_s3_bucket: {
    label: 'S3 bucket',
    does: 'Object storage for files and blobs.',
    usedFor: 'Assets, backups, logs, data lakes, and static websites.',
  },
  aws_efs_file_system: {
    label: 'EFS file system',
    does: 'Shared network file system for multiple instances.',
    usedFor: 'Shared app storage across EC2 / containers.',
  },

  // —— AWS database ——
  aws_db_instance: {
    label: 'RDS database',
    does: 'Managed relational database instance (MySQL, Postgres, etc.).',
    usedFor: 'Application data that needs SQL and managed backups.',
  },
  aws_rds_cluster: {
    label: 'Aurora / RDS cluster',
    does: 'Multi-node managed database cluster.',
    usedFor: 'Higher-availability SQL workloads.',
  },
  aws_dynamodb_table: {
    label: 'DynamoDB table',
    does: 'Managed NoSQL key-value / document store.',
    usedFor: 'Low-latency app state, sessions, and event data.',
  },
  aws_elasticache_cluster: {
    label: 'ElastiCache',
    does: 'Managed in-memory cache (Redis / Memcached).',
    usedFor: 'Caching, sessions, and fast ephemeral data.',
  },

  // —— AWS network ——
  aws_vpc: {
    label: 'VPC',
    does: 'Isolated virtual network for your AWS resources.',
    usedFor: 'Boundary and IP addressing for the whole estate (usually free).',
  },
  aws_subnet: {
    label: 'Subnet',
    does: 'IP range segment inside a VPC (public or private).',
    usedFor: 'Placing resources in zones and controlling exposure.',
  },
  aws_internet_gateway: {
    label: 'Internet gateway',
    does: 'Allows public internet access in and out of a VPC.',
    usedFor: 'Public subnets and internet-facing services.',
  },
  aws_nat_gateway: {
    label: 'NAT gateway',
    does: 'Lets private subnets reach the internet without inbound exposure.',
    usedFor: 'Outbound updates/APIs from private workloads.',
  },
  aws_lb: {
    label: 'Load balancer',
    does: 'Distributes traffic across targets (ALB/NLB).',
    usedFor: 'Public or internal entry points to apps.',
  },
  aws_alb: {
    label: 'Application load balancer',
    does: 'HTTP/HTTPS load balancer with path and host routing.',
    usedFor: 'Web apps and APIs behind a single endpoint.',
  },
  aws_security_group: {
    label: 'Security group',
    does: 'Virtual firewall rules for instances and services.',
    usedFor: 'Allowing or denying network traffic (usually free).',
  },
  aws_route_table: {
    label: 'Route table',
    does: 'Defines where subnet traffic is routed.',
    usedFor: 'Connecting subnets to gateways and peers.',
  },
  aws_eip: {
    label: 'Elastic IP',
    does: 'Static public IPv4 address in AWS.',
    usedFor: 'Stable public endpoints for VMs or NAT.',
  },

  // —— AWS identity ——
  aws_iam_role: {
    label: 'IAM role',
    does: 'Identity that AWS services or users can assume.',
    usedFor: 'Permissions for apps, Lambdas, and EC2 (usually free).',
  },
  aws_iam_policy: {
    label: 'IAM policy',
    does: 'JSON permission document attached to identities.',
    usedFor: 'Fine-grained access control (usually free).',
  },
  aws_iam_user: {
    label: 'IAM user',
    does: 'Long-lived human or machine identity in the account.',
    usedFor: 'CLI/API access with user credentials (prefer roles).',
  },

  // —— Azure ——
  azurerm_linux_virtual_machine: {
    label: 'Linux VM',
    does: 'Runs a Linux virtual machine in Azure.',
    usedFor: 'App servers, jump boxes, and general compute.',
  },
  azurerm_windows_virtual_machine: {
    label: 'Windows VM',
    does: 'Runs a Windows virtual machine in Azure.',
    usedFor: 'Windows apps, RDP jump boxes, and similar workloads.',
  },
  azurerm_virtual_machine: {
    label: 'Virtual machine',
    does: 'Classic Azure VM resource.',
    usedFor: 'General-purpose compute in a resource group.',
  },
  azurerm_managed_disk: {
    label: 'Managed disk',
    does: 'Block disk managed by Azure for VMs.',
    usedFor: 'OS and data disks attached to virtual machines.',
  },
  azurerm_storage_account: {
    label: 'Storage account',
    does: 'Namespace for Azure blobs, files, queues, and tables.',
    usedFor: 'Object storage, shares, and app data persistence.',
  },
  azurerm_mssql_database: {
    label: 'Azure SQL database',
    does: 'Managed SQL Server database.',
    usedFor: 'Relational app data with Azure management.',
  },
  azurerm_mssql_server: {
    label: 'Azure SQL server',
    does: 'Logical SQL Server that hosts databases.',
    usedFor: 'Grouping and securing Azure SQL databases.',
  },
  azurerm_postgresql_flexible_server: {
    label: 'PostgreSQL flexible server',
    does: 'Managed PostgreSQL instance in Azure.',
    usedFor: 'Postgres-backed applications.',
  },
  azurerm_kubernetes_cluster: {
    label: 'AKS cluster',
    does: 'Managed Kubernetes control plane in Azure.',
    usedFor: 'Container orchestration and microservices.',
  },
  azurerm_lb: {
    label: 'Azure load balancer',
    does: 'Distributes network traffic to backend pools.',
    usedFor: 'High availability for VMs and services.',
  },
  azurerm_public_ip: {
    label: 'Public IP',
    does: 'Assignable public address in Azure.',
    usedFor: 'Internet-facing VMs, LBs, and gateways.',
  },
  azurerm_virtual_network: {
    label: 'Virtual network',
    does: 'Isolated network space in Azure (like a VPC).',
    usedFor: 'Addressing and isolation for Azure resources.',
  },
  azurerm_subnet: {
    label: 'Subnet',
    does: 'Segment of an Azure virtual network.',
    usedFor: 'Placing NICs, private endpoints, and services.',
  },
  azurerm_network_security_group: {
    label: 'Network security group',
    does: 'Firewall rules for Azure subnets or NICs.',
    usedFor: 'Controlling inbound/outbound traffic.',
  },
  azurerm_app_service: {
    label: 'App Service',
    does: 'Managed web app hosting platform.',
    usedFor: 'HTTP APIs and websites without managing VMs.',
  },
  azurerm_container_app: {
    label: 'Container App',
    does: 'Serverless container hosting on Azure.',
    usedFor: 'Microservices with scale-to-zero options.',
  },

  // —— GCP ——
  google_compute_instance: {
    label: 'Compute Engine VM',
    does: 'Runs a virtual machine on Google Cloud.',
    usedFor: 'App servers and general compute workloads.',
  },
  google_compute_disk: {
    label: 'Persistent disk',
    does: 'Block storage attached to Compute Engine VMs.',
    usedFor: 'OS and data disks for GCP instances.',
  },
  google_storage_bucket: {
    label: 'Cloud Storage bucket',
    does: 'Object storage for unstructured data.',
    usedFor: 'Assets, backups, data lakes, and static sites.',
  },
  google_sql_database_instance: {
    label: 'Cloud SQL instance',
    does: 'Managed MySQL / Postgres / SQL Server.',
    usedFor: 'Relational databases without self-managing hosts.',
  },
  google_container_cluster: {
    label: 'GKE cluster',
    does: 'Managed Kubernetes cluster on GCP.',
    usedFor: 'Containerized services and workloads.',
  },
  google_compute_network: {
    label: 'VPC network',
    does: 'Global or regional virtual network in GCP.',
    usedFor: 'Connecting and isolating GCP resources.',
  },
  google_compute_subnetwork: {
    label: 'Subnet',
    does: 'Regional IP range inside a GCP VPC.',
    usedFor: 'Placing VMs and private services.',
  },
  google_compute_firewall: {
    label: 'Firewall rule',
    does: 'Allows or denies traffic to GCP instances.',
    usedFor: 'Network security for Compute Engine.',
  },
  google_compute_forwarding_rule: {
    label: 'Forwarding rule',
    does: 'Entry point that forwards traffic to backends.',
    usedFor: 'Load balancing and public/private service fronts.',
  },
  google_compute_global_address: {
    label: 'Global address',
    does: 'Reserved global IP for GCP load balancers.',
    usedFor: 'Stable public endpoints for global services.',
  },
  google_secret_manager_secret: {
    label: 'Secret Manager secret',
    does: 'Stores a named secret (API keys, passwords, config) in GCP.',
    usedFor: 'Centralized credentials apps and Cloud Run can read at runtime.',
  },
  google_secret_manager_secret_version: {
    label: 'Secret Manager version',
    does: 'A versioned payload of a Secret Manager secret.',
    usedFor: 'Rolling secret values without renaming the secret.',
  },
  google_artifact_registry_repository: {
    label: 'Artifact Registry',
    does: 'Stores container images and language packages in GCP.',
    usedFor: 'Hosting images for Cloud Run, GKE, and CI/CD pipelines.',
  },
  google_cloud_tasks_queue: {
    label: 'Cloud Tasks queue',
    does: 'Managed queue that dispatches HTTP/App Engine tasks asynchronously.',
    usedFor: 'Background jobs, retries, and rate-limited fan-out (e.g. notifications).',
  },
  google_service_account: {
    label: 'Service account',
    does: 'Non-human GCP identity that workloads assume.',
    usedFor: 'Least-privilege access for Cloud Run, VMs, and automation.',
  },
  google_cloud_run_v2_service: {
    label: 'Cloud Run service',
    does: 'Runs containers on a managed serverless platform.',
    usedFor: 'HTTP APIs and web apps that scale with traffic.',
  },
  google_cloud_run_service: {
    label: 'Cloud Run service',
    does: 'Runs containers on a managed serverless platform.',
    usedFor: 'HTTP APIs and web apps that scale with traffic.',
  },
  google_cloud_run_v2_job: {
    label: 'Cloud Run job',
    does: 'Runs a container to completion on Cloud Run (batch / one-shot).',
    usedFor: 'Migrations, collectstatic, indexing, and other ops tasks.',
  },
  google_cloud_run_v2_service_iam_member: {
    label: 'Cloud Run IAM member',
    does: 'Grants a principal permission to invoke or admin a Cloud Run service.',
    usedFor: 'Allowing public or service-to-service access to the service.',
  },
  google_cloud_run_v2_job_iam_member: {
    label: 'Cloud Run job IAM member',
    does: 'Grants a principal permission to run or admin a Cloud Run job.',
    usedFor: 'Scheduler / CI identities that trigger batch jobs.',
  },
  google_cloud_scheduler_job: {
    label: 'Cloud Scheduler job',
    does: 'Cron-like managed job that triggers HTTP, Pub/Sub, or App Engine on a schedule.',
    usedFor: 'Periodic tasks — cleanup, digests, re-engage jobs, health pings.',
  },
  google_project_service: {
    label: 'Project service',
    does: 'Enables a Google Cloud API on the project.',
    usedFor: 'Turning on APIs (Run, SQL, Secret Manager, …) before other resources.',
  },
  google_storage_bucket_object: {
    label: 'Bucket object',
    does: 'A file or blob stored in a Cloud Storage bucket.',
    usedFor: 'Scripts, static assets, config archives, and deployment artifacts.',
  },
  google_storage_bucket_iam_member: {
    label: 'Bucket IAM member',
    does: 'Grants a principal access to a Cloud Storage bucket.',
    usedFor: 'Least-privilege read/write for apps and CI identities.',
  },
  google_storage_bucket_iam_binding: {
    label: 'Bucket IAM binding',
    does: 'Authoritative IAM role binding on a Cloud Storage bucket.',
    usedFor: 'Controlling who can list, read, or write bucket objects.',
  },
  google_storage_bucket_iam_policy: {
    label: 'Bucket IAM policy',
    does: 'Full IAM policy document for a Cloud Storage bucket.',
    usedFor: 'Locking down bucket access as a whole.',
  },
  random_id: {
    label: 'Random id',
    does: 'Generates a random byte id for unique resource names.',
    usedFor: 'Suffixes on buckets, passwords, and other globally unique names.',
  },
  random_password: {
    label: 'Random password',
    does: 'Generates a random password string in Terraform state.',
    usedFor: 'Bootstrapping DB users and app secrets (prefer Secret Manager for runtime).',
  },
  terraform_data: {
    label: 'Data (Terraform)',
    does: 'Terraform-managed data/trigger resource with no cloud API object of its own.',
    usedFor: 'Replace triggers, scripted provisioners, and lifecycle hooks.',
  },
  null_resource: {
    label: 'Null resource',
    does: 'Placeholder that can run provisioners or depend on other resources.',
    usedFor: 'One-off scripts and orchestration that is not a real cloud SKU.',
  },
};

const PATTERNS: Array<{ test: (t: string) => boolean; explain: ResourceExplain }> = [
  {
    test: (t) =>
      t.includes('service_account') ||
      t.includes('secret_manager') ||
      t.includes('iam_') ||
      t.includes('_iam_') ||
      t.includes('random_password') ||
      (t.includes('policy') && !t.includes('bucket') && !t.includes('storage')) ||
      t.includes('security_group') ||
      t.includes('firewall'),
    explain: {
      label: 'Identity / security',
      does: 'Controls who and what can access resources.',
      usedFor: 'Permissions, secrets, and access rules.',
    },
  },
  {
    test: (t) => t.includes('cloud_scheduler'),
    explain: {
      label: 'Scheduled job',
      does: 'Fires work on a cron schedule.',
      usedFor: 'Periodic background and maintenance tasks.',
    },
  },
  {
    test: (t) => t.includes('project_service'),
    explain: {
      label: 'Project service',
      does: 'Enables a cloud API on the project.',
      usedFor: 'Prerequisites for other managed services.',
    },
  },
  {
    test: (t) => t.includes('random_id'),
    explain: {
      label: 'Random id',
      does: 'Generates a random identifier.',
      usedFor: 'Unique name suffixes for cloud resources.',
    },
  },
  {
    test: (t) => t.includes('bucket_object') || t.includes('storage_object'),
    explain: {
      label: 'Bucket object',
      does: 'A file stored in object storage.',
      usedFor: 'Scripts, assets, and config blobs.',
    },
  },
  {
    test: (t) => t.includes('terraform_data') || t.includes('null_resource'),
    explain: {
      label: 'Data / script hook',
      does: 'Terraform-side data or provisioner hook, not a billed cloud SKU.',
      usedFor: 'Scripts, triggers, and orchestration helpers.',
    },
  },
  {
    test: (t) => t.includes('virtual_machine') || t.endsWith('_instance') || t.includes('aws_instance'),
    explain: {
      label: 'Compute instance',
      does: 'Provides virtual machine compute capacity.',
      usedFor: 'Running application or system workloads.',
    },
  },
  {
    test: (t) => t.includes('lambda') || t.includes('function_app') || t.includes('cloudfunctions'),
    explain: {
      label: 'Serverless function',
      does: 'Runs code on events or HTTP without a dedicated server.',
      usedFor: 'APIs, automation, and event-driven tasks.',
    },
  },
  {
    test: (t) => t.includes('kubernetes') || t.includes('eks') || t.includes('aks') || t.includes('gke') || t.includes('container_cluster'),
    explain: {
      label: 'Kubernetes cluster',
      does: 'Orchestrates containers across worker nodes.',
      usedFor: 'Microservices and container platforms.',
    },
  },
  {
    test: (t) => t.includes('db_') || t.includes('sql') || t.includes('rds') || t.includes('cosmos') || t.includes('dynamodb'),
    explain: {
      label: 'Database',
      does: 'Stores structured or managed application data.',
      usedFor: 'Persistent app state and queries.',
    },
  },
  {
    test: (t) =>
      (t.includes('bucket') || t.includes('storage_account') || t.includes('storage_bucket')) &&
      !t.includes('iam'),
    explain: {
      label: 'Object storage',
      does: 'Stores files and objects at scale.',
      usedFor: 'Assets, backups, logs, and data lakes.',
    },
  },
  {
    test: (t) => t.includes('disk') || t.includes('ebs') || t.includes('volume'),
    explain: {
      label: 'Block storage',
      does: 'Provides disk capacity for compute.',
      usedFor: 'OS disks, databases, and attached data volumes.',
    },
  },
  {
    test: (t) => t.includes('lb') || t.includes('load_balancer') || t.includes('forwarding_rule') || t.includes('application_gateway'),
    explain: {
      label: 'Load balancer',
      does: 'Distributes incoming traffic across backends.',
      usedFor: 'Reliable, scalable entry points to services.',
    },
  },
  {
    test: (t) => t.includes('vpc') || t.includes('virtual_network') || t.includes('subnet') || t.includes('network'),
    explain: {
      label: 'Network fabric',
      does: 'Defines connectivity and addressing for resources.',
      usedFor: 'Isolation, routing, and placement of services.',
    },
  },
  {
    test: (t) => t.includes('artifact_registry') || t.includes('container_registry') || t.includes('ecr_'),
    explain: {
      label: 'Artifact registry',
      does: 'Stores container images or build artifacts.',
      usedFor: 'Deploying containers and packages from CI/CD.',
    },
  },
  {
    test: (t) => t.includes('cloud_tasks') || t.includes('sqs') || t.includes('pubsub') || t.includes('servicebus'),
    explain: {
      label: 'Async messaging',
      does: 'Queues or topics for background and event-driven work.',
      usedFor: 'Decoupling producers from workers and retries.',
    },
  },
];

export function explainResource(type: string): ResourceExplain {
  const exact = BY_TYPE[type];
  if (exact) return exact;

  const t = type.toLowerCase();
  for (const p of PATTERNS) {
    if (p.test(t)) return p.explain;
  }

  const short = type.includes('_') ? type.split('_').slice(1).join(' ') : type;
  return {
    label: short.replace(/\b\w/g, (c) => c.toUpperCase()),
    does: `Terraform-managed cloud resource (${type}).`,
    usedFor: 'Part of the scanned infrastructure estate.',
  };
}
