from troposphereWrapper.iam import *

def get_iam() -> Role:
  helper = RoleBuilderHelper()
  s3FullAccessPolicy = helper.s3FullAccessPolicy()
  pipeAccessPolicy = helper.awsCodePipelineCustomActionAccess()
  logsAccessPolicy = helper.oneClickCreateLogsPolicy()
  return RoleBuilder() \
    .setName("exampleIAMRole") \
    .setAssumePolicy(
      helper.defaultAssumeRolePolicyDocument("lambda.amazonaws.com")
      ) \
      .addPolicy(s3FullAccessPolicy) \
      .addPolicy(pipeAccessPolicy) \
      .addPolicy(logsAccessPolicy) \
      .build()