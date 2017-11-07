#!/bin/bash

# NOTE: Ideally, we would like to perform the following task in Terraform

pip install -r ../requirements.txt -t build
cp main.py build/
cp -r ../finance build/
cd build
zip -r ../fetch_asset_values.zip .
