from troposphereWrapper.iam import *

def get_iam(stage: str) -> Role:
  helper = RoleBuilderHelper()
  s3FullAccessPolicy = helper.s3FullAccessPolicy()
  pipeAccessPolicy = helper.awsCodePipelineCustomActionAccess()
  logsAccessPolicy = helper.oneClickCreateLogsPolicy()
  return RoleBuilder() \
    .setName("exampleIAMRole" + stage) \
    .setAssumePolicy(
      helper.defaultAssumeRolePolicyDocument("lambda.amazonaws.com")
      ) \
      .addPolicy(s3FullAccessPolicy) \
      .addPolicy(pipeAccessPolicy) \
      .addPolicy(logsAccessPolicy) \
      .build()