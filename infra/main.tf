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
# `fetch_asset_values` resource, but I haven't figured out how to do so.
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

resource "aws_lambda_function" "request_import_stock_values" {
  s3_bucket        = "${var.s3_bucket}"
  s3_key           = "${var.lambda_filename}"
  function_name    = "request_import_stock_values"
  role             = "${data.aws_iam_role.iam_for_lambda.arn}"
  handler          = "lambda.request_import_stock_values_handler"
  source_code_hash = "${var.lambda_filename}"
  runtime          = "python3.6"
  timeout          = 180

  depends_on = ["null_resource.build_lambda"]

  environment {
    variables = {
      SBF_DB_URL = "${var.db_url}"
    }
  }
}

resource "aws_lambda_function" "fetch_asset_values" {
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
      SBF_DB_URL = "${var.db_url}"
    }
  }
}

# NOTE: Without this permission, we would have to set up CloudWatch as an event
# source for Lambda
resource "aws_lambda_permission" "allow_cloudwatch_for_request_import_stock_values" {
  statement_id   = "AllowExecutionFromCloudWatch"
  action         = "lambda:InvokeFunction"
  function_name  = "${aws_lambda_function.request_import_stock_values.id}"
  principal      = "events.amazonaws.com"
  source_arn     = "${aws_cloudwatch_event_rule.event_rule_daily.arn}"
}

resource "aws_lambda_permission" "allow_cloudwatch_for_fetch_asset_values" {
  statement_id   = "AllowExecutionFromCloudWatch"
  action         = "lambda:InvokeFunction"
  function_name  = "${aws_lambda_function.fetch_asset_values.id}"
  principal      = "events.amazonaws.com"
  source_arn     = "${aws_cloudwatch_event_rule.event_rule_every_minute.arn}"
}

resource "aws_cloudwatch_event_target" "event_target_request_import_stock_values" {
  target_id = "${aws_lambda_function.request_import_stock_values.id}"
  rule      = "${aws_cloudwatch_event_rule.event_rule_daily.name}"
  arn       = "${aws_lambda_function.request_import_stock_values.arn}"
}

resource "aws_cloudwatch_event_target" "event_target_fetch_asset_values" {
  target_id = "${aws_lambda_function.fetch_asset_values.id}"
  rule      = "${aws_cloudwatch_event_rule.event_rule_every_minute.name}"
  arn       = "${aws_lambda_function.fetch_asset_values.arn}"
}

resource "aws_cloudwatch_event_rule" "event_rule_daily" {
  name                = "event_rule_daily"
  description         = "Periodic event"
  schedule_expression = "cron(0 0 * * ? *)"
}

resource "aws_cloudwatch_event_rule" "event_rule_every_minute" {
  name                = "event_rule_every_minute"
  description         = "Periodic event"
  schedule_expression = "cron(* * * * ? *)"
}

# NOTE: Could we launch a Lambda to install packages via pip and zip them up?
# TODO: Make a process to package the code and upload to S3

