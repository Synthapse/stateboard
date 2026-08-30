/** Minimal multi-cloud fixture for demos / tests */
export const SAMPLE_TFSTATE = {
  version: 4,
  terraform_version: '1.9.0',
  serial: 1,
  lineage: 'stateboard-sample',
  resources: [
    {
      mode: 'managed',
      type: 'aws_instance',
      name: 'web',
      provider: 'provider["registry.terraform.io/hashicorp/aws"]',
      instances: [
        {
          attributes: { instance_type: 't3.micro', region: 'us-east-1' },
          dependencies: [],
        },
      ],
    },
    {
      mode: 'managed',
      type: 'aws_iam_user',
      name: 'ci',
      provider: 'provider["registry.terraform.io/hashicorp/aws"]',
      instances: [{ attributes: {}, dependencies: [] }],
    },
    {
      module: 'module.db',
      mode: 'managed',
      type: 'azurerm_linux_virtual_machine',
      name: 'app',
      provider: 'provider["registry.terraform.io/hashicorp/azurerm"]',
      instances: [
        {
          attributes: { size: 'Standard_D2s_v3', location: 'westeurope' },
          dependencies: [],
        },
      ],
    },
    {
      mode: 'managed',
      type: 'google_compute_instance',
      name: 'batch',
      provider: 'provider["registry.terraform.io/hashicorp/google"]',
      instances: [
        {
          attributes: { machine_type: 'e2-micro', region: 'us-central1' },
          dependencies: [],
        },
      ],
    },
  ],
};
