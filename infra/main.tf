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

resource "aws_lambda_function" "fetch_asset_values_lambda" {
  filename         = "fetch_asset_values.zip"
  function_name    = "fetch_asset_values"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "main.handler"
  source_code_hash = "${base64sha256(file("fetch_asset_values.zip"))}"
  runtime          = "python3.6"
}
