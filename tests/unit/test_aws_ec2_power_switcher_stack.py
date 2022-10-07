import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_ec2_power_switcher.aws_ec2_power_switcher_stack import AwsEc2PowerSwitcherStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_ec2_power_switcher/aws_ec2_power_switcher_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsEc2PowerSwitcherStack(app, "aws-ec2-power-switcher")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
