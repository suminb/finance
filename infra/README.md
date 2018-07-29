Infrastructure
==============

Some of the code is intended to run on AWS, and thus we use
[Terraform](https://www.terraform.io) to manage our infrastructure.

Deployment
----------

Make sure nothing shady is going on by inspecting a plan. The `db_url` variable
is not included in `main.tf` for obvious (security) reasons, so it needs to be
injected via a command line parameter.

```
terraform plan -var db_url="<DB URL>"
```

If all is good, apply the plan on the live environment.

```
terraform apply -var db_url="<DB URL>"
```

Notes
-----

- When `apply` operation is done, `terraform.tfstate` file, which contains the
  state of all AWS resources, is updated.
- For some reason, AWS credentials stored in `~/.aws/credentials` seem to have
  no effect. Providing them via environment variables (`AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`) works fine.
