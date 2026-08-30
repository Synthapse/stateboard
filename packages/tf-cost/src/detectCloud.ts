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
  if (/instance|virtual_machine|compute_instance/.test(t)) return 'compute';
  if (/vpc|subnet|vnet|network|security_group|firewall/.test(t)) return 'network';
  if (/s3|storage_account|bucket|ebs|disk|volume/.test(t)) return 'storage';
  if (/db_|rds|sql_|database|cosmos/.test(t)) return 'database';
  if (/iam_|role|policy|user|service_account/.test(t)) return 'identity';
  return 'generic';
}
