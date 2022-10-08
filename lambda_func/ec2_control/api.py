from flask import Flask, request, json, jsonify, make_response
import boto3
import os

app = Flask(__name__)

region = os.environ.get('AWS_REGION') or 'us-east-1'
ec2 = boto3.client('ec2', region_name=region)


@app.route("/ec2/poweron", methods=['POST'])
def power_on_ec2():
    context = request.environ.get('serverless.context')
    event = request.environ.get('serverless.event')
    body = json.loads(event['body'])
    instance_ids = body['instance_ids']

    if instance_ids:
        ec2.start_instances(InstanceIds=instance_ids)

    return jsonify({
        "message": "OK",
        "targets": instance_ids
    })


@app.route("/ec2/poweroff", methods=['POST'])
def power_off_ec2():
    context = request.environ.get('serverless.context')
    event = request.environ.get('serverless.event')
    body = json.loads(event['body'])
    instance_ids = body['instance_ids']

    if instance_ids:
        ec2.stop_instances(InstanceIds=instance_ids)

    return jsonify({
        "message": "OK",
        "targets": instance_ids
    })


@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)
