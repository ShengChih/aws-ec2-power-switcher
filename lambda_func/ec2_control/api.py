from flask import Flask, request, json, jsonify, make_response
from functools import reduce

import boto3
import os
from botocore.exceptions import ClientError


app = Flask(__name__)

region = os.environ.get('AWS_REGION') or 'us-east-1'
ec2 = boto3.client('ec2', region_name=region)


def parser_describe_response(response):
    ret = dict()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            ret[instance['InstanceId']] = instance['PublicIpAddress'] \
                if 'PublicIpAddress' in instance else None

    return ret


def parser_address_response(response):
    return reduce(
        lambda ret, allocation_id: ret.union(allocation_id),
        list(
            map(
                lambda address: address['AllocationId'],
                response['Addresses']
            )
        ),
        set()
    )


def allocate_elastic_ip():
    """
    Allocates an Elastic IP address that can be associated with an instance. By using
    an Elastic IP address, you can keep the public IP address constant even when you
    change the associated instance.

    :return: The newly created Elastic IP object. By default, the address is not
             associated with any instance.
    """
    try:
        response = ec2.meta.client.allocate_address(Domain='vpc')
        elastic_ip = ec2.VpcAddress(response['AllocationId'])
        # logger.info("Allocated Elastic IP %s.", elastic_ip.public_ip)
    except ClientError:
        # logger.exception("Couldn't allocate Elastic IP.")
        raise
    else:
        return response['AllocationId'], elastic_ip


def associate_elastic_ip(allocation_id, instance_id):
    """
    Associates an Elastic IP address with an instance. When this association is
    created, the Elastic IP's public IP address is immediately used as the public
    IP address of the associated instance.

    :param allocation_id: The allocation ID assigned to the Elastic IP when it was
                          created.
    :param instance_id: The ID of the instance to associate with the Elastic IP.
    :return: The Elastic IP object.
    """
    try:
        elastic_ip = ec2.VpcAddress(allocation_id)
        elastic_ip.associate(InstanceId=instance_id)
        # logger.info("Associated Elastic IP %s with instance %s, got association ID %s",
        #             elastic_ip.public_ip, instance_id, elastic_ip.association_id)
    except ClientError:
        # logger.exception(
        #     "Couldn't associate Elastic IP %s with instance %s.",
        #     allocation_id, instance_id)
        raise
    return elastic_ip


def disassociate_elastic_ip(allocation_id):
    """
    Removes an association between an Elastic IP address and an instance. When the
    association is removed, the instance is assigned a new public IP address.

    :param allocation_id: The allocation ID assigned to the Elastic IP address when
                          it was created.
    """
    try:
        elastic_ip = ec2.VpcAddress(allocation_id)
        elastic_ip.association.delete()
        # logger.info(
        #     "Disassociated Elastic IP %s from its instance.", elastic_ip.public_ip)
    except ClientError:
        # logger.exception(
        #     "Couldn't disassociate Elastic IP %s from its instance.", allocation_id)
        raise


def release_elastic_ip(allocation_id):
    """
    Releases an Elastic IP address. After the Elastic IP address is released,
    it can no longer be used.

    :param allocation_id: The allocation ID assigned to the Elastic IP address when
                          it was created.
    """
    try:
        elastic_ip = ec2.VpcAddress(allocation_id)
        elastic_ip.release()
        # logger.info("Released Elastic IP address %s.", allocation_id)
    except ClientError:
        # logger.exception(
        #     "Couldn't release Elastic IP address %s.", allocation_id)
        raise


@app.route("/ec2/poweron", methods=['POST'])
def power_on_ec2():
    context = request.environ.get('serverless.context')
    event = request.environ.get('serverless.event')
    body = json.loads(event['body'])
    instance_ids = body['instance_ids']

    try:
        if not instance_ids:
            raise

        response = ec2.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['stopped'],
                }
            ],
        )

        stopped_instance_ids = set(parser_describe_response(response).keys())
        target_instance_ids = set(instance_ids)
        intersection_instance_ids = list(
            stopped_instance_ids.intersection(target_instance_ids)
        )

        if not intersection_instance_ids:
            raise

        ec2.start_instances(InstanceIds=intersection_instance_ids)

        return jsonify({
            "message": "OK",
            "targets": intersection_instance_ids
        })
    except Exception:
        return jsonify({
            "message": "OK",
            "targets": []
        })


@app.route("/ec2/poweroff", methods=['POST'])
def power_off_ec2():
    context = request.environ.get('serverless.context')
    event = request.environ.get('serverless.event')
    body = json.loads(event['body'])
    instance_ids = body['instance_ids']

    try:
        if not instance_ids:
            raise

        response = ec2.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['running'],
                }
            ],
        )
        running_instance_ids = set(parser_describe_response(response).keys())
        target_instance_ids = set(instance_ids)
        intersection_instance_ids = list(
            running_instance_ids.intersection(target_instance_ids)
        )

        if not intersection_instance_ids:
            raise

        ec2.stop_instances(InstanceIds=intersection_instance_ids)

        return jsonify({
            "message": "OK",
            "targets": intersection_instance_ids
        })
    except Exception:
        return jsonify({
            "message": "OK",
            "targets": []
        })


@app.route("/ec2/info", methods=['GET'])
def describe_ec2():
    context = request.environ.get('serverless.context')
    event = request.environ.get('serverless.event')
    instance_id = event['queryStringParameters']['instance_id'] \
        if 'instance_id' in event['queryStringParameters'] else ""

    try:
        if not instance_id:
            raise

        response = ec2.describe_instances(
            InstanceIds=[instance_id]
        )
        describe_list = parser_describe_response(response)

        return jsonify({
            "message": "OK",
            "targets": describe_list
        })
    except Exception:
        return jsonify({
            "message": "OK"
        })


@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)
