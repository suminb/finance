#!/bin/bash

set -e

# NOTE: Ideally, we would like to perform the following task in Terraform

S3_BUCKET="suminb-test"
ARTIFACT="fetch_asset_values.zip"

# pip install -r ../requirements.txt -t build
# NOTE: Instead of directly building Python requirements, we pre-built those
# packages on an Amazon Linux instance and made an archive.
aws s3 cp s3://$S3_BUCKET/build.tgz .
rm -rf build
tar zxf build.tgz

cp lambda.py build/
cp -r ../finance build/
pushd build
find . -name "*.pyc" -delete
find . -name __pycache__ -delete
rm -rf $(find . -name tests)
rm ../$ARTIFACT
zip -r ../$ARTIFACT .
popd
aws s3 cp fetch_asset_values.zip s3://$S3_BUCKET/
