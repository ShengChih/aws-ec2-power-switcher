from aws_cdk import (
    # Duration,
    Stack,
    aws_cognito,
    aws_lambda,
    aws_apigateway,
    # aws_certificatemanager,
    aws_iam,
    aws_logs
)
from constructs import Construct
from pathlib import Path
import os


class AwsEc2PowerSwitcherStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        user_pool = aws_cognito.UserPool(
            self,
            "ApiUserPool",
            self_sign_up_enabled=False,
            user_pool_name="ApiUserPool",
        )
        user_pool_cfn = user_pool.node.default_child
        user_pool_cfn.alias_attributes = ["email"]
        user_pool_cfn.auto_verified_attributes = ["email"]
        user_pool_cfn.verification_message_template = aws_cognito.CfnUserPool.VerificationMessageTemplateProperty(
            default_email_option="CONFIRM_WITH_LINK",
        )
        # user_pool = aws_cognito.CfnUserPool(
        #    self,
        #    "ApiUserPool",
        #    alias_attributes=["email"],
        #    auto_verified_attributes=["email"],
        #    user_pool_name="ApiUserPool",
        #    verification_message_template=aws_cognito.CfnUserPool.VerificationMessageTemplateProperty(
        #        default_email_option="CONFIRM_WITH_LINK",
        #    )
        # )

        user_pool_client = aws_cognito.UserPoolClient(
            self,
            "ApiUserClient",
            user_pool=user_pool,
            auth_flows=aws_cognito.AuthFlow(
                user_password=True
            ),
        )
        cfn_user_pool_client = user_pool_client.node.default_child
        cfn_user_pool_client.explicit_auth_flows = [
            "ALLOW_REFRESH_TOKEN_AUTH",
            "ALLOW_USER_PASSWORD_AUTH"
        ]
        cfn_user_pool_client.supported_identity_providers = ["COGNITO"]

        # cfn_user_pool_client = aws_cognito.CfnUserPoolClient(
        #     self,
        #     "ApiUserClient",
        #     user_pool_id=user_pool.ref,
        #     # the properties below are optional
        #     explicit_auth_flows=[
        #         "ALLOW_REFRESH_TOKEN_AUTH",
        #         "ALLOW_USER_PASSWORD_AUTH"
        #     ],
        #     generate_secret=False,
        #     supported_identity_providers=["COGNITO"]
        # )

        # certificate_arn = os.environ.get("C_ARN")
        user_pool_domain = aws_cognito.UserPoolDomain(
            self,
            "ApiUserDomain",
            user_pool=user_pool,
            cognito_domain=aws_cognito.CognitoDomainOptions(
                domain_prefix=os.environ.get("DOMAIN")
            )
        )
        # cfn_user_pool_domain = aws_cognito.CfnUserPoolDomain(
        #     self,
        #     "ApiUserDomain",
        #     domain=os.environ.get("DOMAIN"),
        #     user_pool_id=user_pool.ref,
        #     # the properties below are optional
        #     # custom_domain_config=aws_cognito.CfnUserPoolDomain.CustomDomainConfigTypeProperty(
        #     #     certificate_arn=certificate_arn
        #     # )
        # )

        # create role
        admin_apigateway_role = aws_iam.Role(
            self,
            "ApigatewayAccessRole",
            role_name="ApigatewayAccessCloudwatchRole",
            assumed_by=aws_iam.ServicePrincipal("apigateway.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    'service-role/AmazonAPIGatewayPushToCloudWatchLogs'
                )
            ]
        )
        ec2_control_lambda_role = aws_iam.Role(
            self,
            "LambdaAccessEC2AndCloudWatch2Role",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com")
        )

        # create managed policy
        lambda_role_policy = aws_iam.ManagedPolicy(
            self,
            'EC2PowerControlPolicy',
            managed_policy_name='EC2PowerControlPolicy',
            statements=[
                aws_iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=["arn:aws:logs:*:*:*"]
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "ec2:StartInstances",
                        "ec2:StopInstances"
                    ],
                    resources=["*"]
                )
            ],
            roles=[ec2_control_lambda_role]
        )

        py37_layer = aws_lambda.LayerVersion(
            self,
            'py37_layer',
            compatible_architectures=[aws_lambda.Architecture.X86_64],
            compatible_runtimes=[aws_lambda.Runtime.PYTHON_3_7],
            code=aws_lambda.Code.from_asset(
                os.path.join(
                    Path(os.path.dirname(__file__)).parent,
                    "lambda_layer",
                    "py37"
                )
            ),
            description="Flask + Werkzeug library"
        )
        ec2_control = aws_lambda.Function(
            self,
            id='ec2_control',
            function_name='ec2_control',
            runtime=aws_lambda.Runtime.PYTHON_3_7,
            handler='wsgi_handler.handler',
            code=aws_lambda.Code.from_asset(
                os.path.join(
                    Path(os.path.dirname(__file__)).parent,
                    "lambda_func"
                )
            ),
            role=ec2_control_lambda_role,
            environment={},
            layers=[py37_layer]
        )

        # production stage
        cfn_account = aws_apigateway.CfnAccount(
            self,
            "ApigatewayAccount",
            cloud_watch_role_arn=admin_apigateway_role.role_arn
        )
        api_log_group = aws_logs.LogGroup(self, "AdminApiLog")
        restapi = aws_apigateway.RestApi(
            self,
            id='AdminApi',
            rest_api_name='AdminApi',
            deploy_options=aws_apigateway.StageOptions(
                access_log_destination=aws_apigateway.LogGroupLogDestination(api_log_group),
                access_log_format=aws_apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True
                )
            )
        )
        # weird point
        cfn_account.node.add_dependency(restapi.node.default_child)

        authorizer = aws_apigateway.CfnAuthorizer(
            self,
            "ApiAuthorizer",
            name="ApiAuthorizer",
            type="COGNITO_USER_POOLS",
            identity_source='method.request.header.Authorization',
            provider_arns=[user_pool_cfn.attr_arn],
            rest_api_id=restapi.rest_api_id
        )

        ec2_resource = restapi.root.add_resource("ec2")

        ec2_poweron_resource = ec2_resource.add_resource("poweron")
        ec2_poweron_method = ec2_poweron_resource.add_method(
            "POST",
            integration=aws_apigateway.LambdaIntegration(
                handler=ec2_control
            )
        )
        ec2_poweron_method_resource = ec2_poweron_method.node \
            .find_child('Resource')
        ec2_poweron_method_resource.add_property_override(
            'AuthorizationType',
            'COGNITO_USER_POOLS'
        )
        ec2_poweron_method_resource.add_property_override(
            'AuthorizerId',
            authorizer.ref
        )

        ec2_poweroff_resource = ec2_resource.add_resource("poweroff")
        ec2_poweroff_method = ec2_poweroff_resource.add_method(
            "POST",
            integration=aws_apigateway.LambdaIntegration(
                handler=ec2_control
            )
        )
        ec2_poweroff_method_resource = ec2_poweroff_method.node \
            .find_child('Resource')
        ec2_poweroff_method_resource.add_property_override(
            'AuthorizationType',
            'COGNITO_USER_POOLS'
        )
        ec2_poweroff_method_resource.add_property_override(
            'AuthorizerId',
            authorizer.ref
        )
        

