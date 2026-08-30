import type { CostFamily } from '../types.js';

export function classifyFamily(type: string): CostFamily {
  const t = type.toLowerCase();
  if (/iam_|random_|null_resource|local_file|tls_|\.data\./.test(t)) return 'free';
  if (/instance$|virtual_machine|compute_instance|launch_template/.test(t)) return 'compute';
  if (/ebs_volume|managed_disk|persistent_disk|disk_attachment/.test(t)) return 'disk';
  if (/s3_bucket$|storage_account|storage_bucket/.test(t)) return 'object';
  if (/db_instance|sql_database|sql_server|rds_|alloydb|spanner/.test(t)) return 'database';
  if (/lb|load_balancer|nat_gateway|natgateway/.test(t)) return 'network';
  if (/security_group|network_acl|route_table|subnet|vpc$|vnet/.test(t)) return 'free';
  return 'other';
}
