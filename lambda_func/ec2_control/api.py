from flask import Flask, jsonify, make_response

app = Flask(__name__)


@app.route("/ec2")
def hello_from_root():
    return jsonify(message='Hello from root!')


@app.route("/ec2/poweron", , methods=['POST'])
def power_on_ec2(instance_id):
    return jsonify({
        "instance_id": instance_id
    })


@app.route("/ec2/poweroff", , methods=['POST'])
def power_off_ec2(instance_id):
    return jsonify({
        "instance_id": instance_id
    })


@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)


