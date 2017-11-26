from troposphereWrapper.iam import *

def get_iam(stage: str, ref_name: str) -> Role:
  helper = RoleBuilderHelper()
  return RoleBuilder() \
    .setName(ref_name) \
    .setAssumePolicy(
      helper.defaultAssumeRolePolicyDocument("lambda.amazonaws.com")
      ) \
      .build()