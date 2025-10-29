#!/bin/sh

set -e

gcloud config set project odai-prod
python run_tests.py --workers 8
gcloud app deploy prod.yaml
echo "Production Deployment Complete"|espeak

