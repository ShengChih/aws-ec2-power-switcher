# AWS EC2 start/stop instance API with cdk

## Requirements:
- [poetry](https://github.com/python-poetry/poetry)
- [aws cdk](https://github.com/aws/aws-cdk)


## Usage:
```shell
aws configure
export AWS_REGION="{aws-region: e.g. us-east-1}"
export DOMAIN="{prefix cognito domain}"
poetry install
source .venv/bin/activate
make output_layer
cdk synth
cdk deploy
```

## Services
- AWS apigateway restapi
- AWS api authorizor + AWS Cognito
- AWS Lambda & Lambda Layer


# Thanks & Refs
- [serverless-wsgi](https://github.com/logandk/serverless-wsgi)
- [start-stop-lambda-eventbridge](https://aws.amazon.com/tw/premiumsupport/knowledge-center/start-stop-lambda-eventbridge/)
