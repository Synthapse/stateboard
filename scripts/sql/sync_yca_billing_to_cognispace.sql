-- Kept in sync with terraform/yca_billing_sync.tf (scheduled query).
-- Manual: BigQuery → Schedule → paste → project cognispace · location EU.

IF (
  SELECT COUNT(*)
  FROM `adroit-router-462912-n6.raw_billing.INFORMATION_SCHEMA.TABLES`
  WHERE table_name = 'gcp_billing_export_resource_v1_01F545_2E8963_C6EBE1'
) > 0
THEN
  CREATE OR REPLACE TABLE
    `cognispace.raw_billing.gcp_billing_export_resource_v1_01F545_2E8963_C6EBE1`
  COPY
    `adroit-router-462912-n6.raw_billing.gcp_billing_export_resource_v1_01F545_2E8963_C6EBE1`;
END IF;
