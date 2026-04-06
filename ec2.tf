resource "aws_instance" "frontend" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.ec2_instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = base64encode(templatefile("${path.module}/user_data.sh.tpl", {
    project_name = var.project_name
    environment  = var.environment
    api_base_url = aws_apigatewayv2_stage.default.invoke_url
  }))

  tags = merge(local.tags, { Name = "${local.name}-frontend" })
}
