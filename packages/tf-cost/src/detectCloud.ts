import type { Cloud, SpriteKind } from './types.js';

export function detectCloud(type: string, provider: string): Cloud {
  const p = provider.toLowerCase();
  const t = type.toLowerCase();
  if (t.startsWith('aws_') || p.includes('/hashicorp/aws')) return 'aws';
  if (t.startsWith('azurerm_') || p.includes('/hashicorp/azurerm')) return 'azure';
  if (t.startsWith('google_') || t.startsWith('google-beta_') || p.includes('/hashicorp/google'))
    return 'gcp';
  return 'other';
}

export function spriteKindFor(type: string): SpriteKind {
  const t = type.toLowerCase();
  const isCloudRun = /cloud_run|cloudrun/.test(t);
  const isIam = /iam_|_iam_|_iam$/.test(t);
  if (isCloudRun && isIam) return 'identity';
  if (isCloudRun) return 'compute';
  if (
    /service_account|secret_manager|_role$|random_password|kms_/.test(t) ||
    isIam ||
    (/policy/.test(t) && !/bucket|storage/.test(t))
  )
    return 'identity';
  if (/artifact_registry|container_registry|ecr_|s3|storage_account|bucket|ebs|disk|volume/.test(t))
    return 'storage';
  if (/db_|rds|sql_|database|cosmos/.test(t)) return 'database';
  if (
    /vpc|subnet|vnet|forwarding_rule|firewall|security_group|route|gateway|load_balancer|_lb\b/.test(t) ||
    /network/.test(t)
  )
    return 'network';
  if (
    /cloud_tasks|cloud_scheduler|cloud_functions|pubsub|sqs|lambda|ecs|instance|virtual_machine|compute|container_cluster|app_service/.test(
      t,
    )
  )
    return 'compute';
  return 'generic';
}
