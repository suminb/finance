provider "aws" {
  region  = "us-west-2"
  profile = "finance"
}

# resource "aws_iam_role" "iam_for_lambda" {
#   name = "iam_for_lambda"
#
#   assume_role_policy = <<EOF
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Action": "sts:AssumeRole",
#       "Principal": {
#         "Service": "lambda.amazonaws.com"
#       },
#       "Effect": "Allow",
#       "Sid": ""
#     }
#   ]
# }
# EOF
# }

data "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda"
}

variable "s3_bucket" {
  default = "finance.brogrammer.xyz"
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
      cp lambda.py build/
      cd build
      zip -r ../fetch_asset_values.zip .
    EOF
  }
}

resource "aws_lambda_function" "request_stock_values_lambda" {
  s3_bucket        = "${var.s3_bucket}"
  s3_key           = "${var.lambda_filename}"
  function_name    = "request_stock_values"
  role             = "${data.aws_iam_role.iam_for_lambda.arn}"
  handler          = "lambda.request_import_stock_values_handler"
  source_code_hash = "${var.lambda_filename}"
  runtime          = "python3.6"
  timeout          = 180

  depends_on = ["null_resource.build_lambda"]

  environment {
    variables = {
      SQS_REGION = "us-west-2"
      REQUEST_IMPORT_STOCK_VALUES_QUEUE_URL = "${aws_sqs_queue.request_import_stock_values.id}"
    }
  }
}

resource "aws_lambda_function" "fetch_asset_values_lambda" {
  s3_bucket        = "${var.s3_bucket}"
  s3_key           = "${var.lambda_filename}"
  function_name    = "fetch_asset_values"
  role             = "${data.aws_iam_role.iam_for_lambda.arn}"
  handler          = "lambda.fetch_asset_values_handler"
  source_code_hash = "${var.lambda_filename}"
  runtime          = "python3.6"
  timeout          = 180

  depends_on = ["null_resource.build_lambda"]

  environment {
    variables = {
      SQS_REGION = "us-west-2"
      REQUEST_IMPORT_STOCK_VALUES_QUEUE_URL = "${aws_sqs_queue.request_import_stock_values.id}"
    }
  }
}

resource "aws_cloudwatch_event_target" "event_target_request_stock_values" {
  target_id = "${aws_lambda_function.request_stock_values_lambda.id}"
  rule      = "${aws_cloudwatch_event_rule.event_rule_daily.name}"
  arn       = "${aws_lambda_function.request_stock_values_lambda.arn}"
}

resource "aws_cloudwatch_event_target" "event_target_fetch_asset_values" {
  target_id = "${aws_lambda_function.fetch_asset_values_lambda.id}"
  rule      = "${aws_cloudwatch_event_rule.event_rule_hourly.name}"
  arn       = "${aws_lambda_function.fetch_asset_values_lambda.arn}"
}

resource "aws_cloudwatch_event_rule" "event_rule_daily" {
  name                = "event_rule_daily"
  description         = "Periodic event"
  schedule_expression = "cron(0 0 * * ? *)"
}

resource "aws_cloudwatch_event_rule" "event_rule_hourly" {
  name                = "event_rule_hourly"
  description         = "Periodic event"
  schedule_expression = "cron(0 * * * ? *)"
}

resource "aws_sqs_queue" "request_import_stock_values" {
  name                      = "finance-request-import-stock-values"
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 345600
}

# NOTE: Could we launch a Lambda to install packages via pip and zip them up?
# TODO: Make a process to package the code and upload to S3

