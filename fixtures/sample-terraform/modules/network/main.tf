resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
}

resource "aws_lb" "app" {
  load_balancer_type = "application"
  subnets            = [aws_subnet.public.id]
}

output "subnet_id" {
  value = aws_subnet.public.id
}
