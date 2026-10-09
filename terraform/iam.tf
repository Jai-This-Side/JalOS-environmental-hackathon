resource "aws_iam_role" "ec2" {
  name = "jalos-ec2-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "runtime" {
  name = "jalos-runtime-${var.environment}"
  role = aws_iam_role.ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = [
          "${aws_s3_bucket.artifacts.arn}/deploy/${var.environment}/*",
          "${aws_s3_bucket.artifacts.arn}/models/*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = aws_ssm_parameter.runtime_environment.arn
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService"                      = "ssm.${data.aws_region.current.name}.amazonaws.com"
            "kms:EncryptionContext:PARAMETER_ARN" = aws_ssm_parameter.runtime_environment.arn
          }
        }
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/jalos/${var.environment}:*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2" {
  name = "jalos-ec2-${var.environment}"
  role = aws_iam_role.ec2.name
}
