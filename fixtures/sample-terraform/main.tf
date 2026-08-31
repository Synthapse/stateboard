terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

module "network" {
  source = "./modules/network"
}

resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t3.micro"
  subnet_id     = module.network.subnet_id

  tags = {
    Name = "web"
  }
}

resource "aws_ebs_volume" "data" {
  availability_zone = "us-east-1a"
  size              = 20
  type              = "gp3"
}

resource "aws_volume_attachment" "data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.data.id
  instance_id = aws_instance.web.id
}

resource "aws_db_instance" "app" {
  engine         = "postgres"
  instance_class = "db.t3.micro"
  allocated_storage = 20
}

resource "aws_s3_bucket" "assets" {
  bucket = "example-assets"
}
