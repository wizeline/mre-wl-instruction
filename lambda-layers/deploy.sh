#!/bin/bash

# $1 refers to the aws-profile argument passed to the script
AWS_PROFILE=$1

# $2 refers to the AWS region argument passed to the script
if [ -z "$2" ]; then
    AWS_DEFAULT_REGION="us-east-1"
else
    AWS_DEFAULT_REGION="$2"
fi

export AWS_PROFILE
export AWS_DEFAULT_REGION

if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

echo "Creating new virtual environment..."
python -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running script..."

# Setup a trap to deactivate the virtual environment upon script exit
trap "echo 'Deactivating virtual environment...'; deactivate" EXIT

python lambda-layers.py