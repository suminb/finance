Infrastructure
==============

Some of the code is intended to run on AWS, and thus we use
[Terraform](https://www.terraform.io) to manage our infrastructure.

Architecture
------------

- `request_import_stock_values` inserts asset codes into SQS.
- `fetch_asset_values` polls asset codes from SQS and actually fetch data from
   a source.
- CloudWatch Alarm invokes both functions periodically.

Build
-----

```
./build.sh
```

NOTE: This fetches a *base system* from S3 (which we previously built and
uploaded). The *base system* contains Python packages built for AWS Lambda
environment (Amazon Linux distro).

Deployment
----------

Make sure nothing shady is going on by inspecting a plan. The `db_url` variable
is not included in `main.tf` for obvious (security) reasons, so it needs to be
injected via a command line parameter.

```
terraform plan -var db_url="postgres://username:password@host:port/database"
```

If all is good, apply the plan on the live environment.

```
terraform apply -var db_url="postgres://username:password@host:port/database"
```

Notes
-----

- When `apply` operation is done, `terraform.tfstate` file, which contains the
  state of all AWS resources, is updated.
- For some reason, AWS credentials stored in `~/.aws/credentials` seem to have
  no effect. Providing them via environment variables (`AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`) works fine.
