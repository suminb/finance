provider "aws" {
  region = "us-west-2"
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

variable "lambda_filename" {
  default = "fetch_asset_values.zip"
}

# NOTE: I would like to execute the following commands before creating the
# `fetch_asset_values_lambda` resource, but I haven't figured out how to do so.
resource "null_resource" "build_lambda" {
  provisioner "local-exec" {
    command = <<EOF
      pip install -r ../requirements.txt -t build
      cp main.py build/
      zip -r fetch_asset_values.zip build
    EOF
  }
}

resource "aws_lambda_function" "fetch_asset_values_lambda" {
  filename         = "${var.lambda_filename}"
  function_name    = "fetch_asset_values"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "main.handler"
  source_code_hash = "${base64sha256(file("${var.lambda_filename}"))}"
  runtime          = "python3.6"

  depends_on = ["null_resource.build_lambda"]
}
