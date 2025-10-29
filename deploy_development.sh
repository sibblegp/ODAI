#!/bin/sh

set -e

gcloud config set project odai-dev
python run_tests.py --workers 8
gcloud app deploy
echo "Development Deployment Complete"|espeak
