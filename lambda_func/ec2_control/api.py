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

    if not instance_ids:
        return jsonify({
            "message": "OK",
            "targets": instance_ids
        })

    instances = ec2.instances.filter(
        Filters=[{
            'Values': ['stopped']
        }]
    )
    stopped_instance_ids = set(list(map(lambda instance: instance.id, instances)))
    target_instance_ids = set(instance_ids)
    intersection_instance_ids = list(
        stopped_instance_ids.intersection(target_instance_ids)
    )

    if not intersection_instance_ids:
        return jsonify({
            "message": "OK",
            "targets": intersection_instance_ids
        })

    ec2.start_instances(InstanceIds=intersection_instance_ids)

    return jsonify({
        "message": "OK",
        "targets": intersection_instance_ids
    })


@app.route("/ec2/poweroff", methods=['POST'])
def power_off_ec2():
    context = request.environ.get('serverless.context')
    event = request.environ.get('serverless.event')
    body = json.loads(event['body'])
    instance_ids = body['instance_ids']

    if not instance_ids:
        return jsonify({
            "message": "OK",
            "targets": instance_ids
        })

    instances = ec2.instances.filter(
        Filters=[{
            'Values': ['running']
        }]
    )
    running_instance_ids = set(list(map(lambda instance: instance.id, instances)))
    target_instance_ids = set(instance_ids)
    intersection_instance_ids = list(
        running_instance_ids.intersection(target_instance_ids)
    )

    if not intersection_instance_ids:
        return jsonify({
            "message": "OK",
            "targets": intersection_instance_ids
        })

    ec2.stop_instances(InstanceIds=intersection_instance_ids)

    return jsonify({
        "message": "OK",
        "targets": intersection_instance_ids
    })


@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)
