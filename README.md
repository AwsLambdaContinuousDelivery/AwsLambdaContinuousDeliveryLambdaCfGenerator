# lambdaCICDBuilder
tl;dr : [ LambdaFunction.py ] -> AWS CloudFormation file

`Python 3.x` script, which will take a folder of python files, which represent lambda functions, and outputs a cloudformation template file which can deploy all the lambda functions

# Instructions

## CodeBuild

This tool is currently build to work with AWS CodeBuild and is using the Python 3 library
`troposphere`, `awacs` and my own wrapper, which contains the dependencies for `troposphere` and `awacs`.

It is tested with the `frolvlad/alpine-python3` docker image (and the following build spec is writting for this image)

Use this build spec for CodeBuild, which will take the functions and outputs an `stack.json` artifact:

```yaml
version: 0.2

phases:
  install:
    commands:
      - apk update
      - apk upgrade
      - apk add --no-cache bash git openssh
  pre_build:
    commands:
      - git clone https://github.com/jpotecki/lambdaCICDBuilder.git
      - pip3 install git+https://github.com/jpotecki/TroposphereWrapper.git
  build:
    commands:
      - ls -a
      - python3 lambdaCICDBuilder/createCF.py $(pwd)/ >> stack.json
artifacts:
  files:
    - stack.json
```


## Folder structure of Lambda Functions

It is important that your functions have the following naming:
- Each function must be in an own folder which bears the name of the function starting with a lower case character
- Each function folder must consists of two `python` files, which start with the name of the function (== foldername) appended with `Function.py` and `IAM.py` respectively
- `{$name}Function.py` must consists the handler function, which has the naming structure `{$name}_handler(event, context)`
- `{$name}IAM.py` must contain a function `get_IAM() -> Role` which returns a `troposphere.iam.Role`
```
func1
| func1Function.py
| func1IAM.py
func2
| func2Function.py
| func2IAM.py
```

Example `func1Function.py`:
```python
from typing import List

def func1_handler(event, context):
  return 0
```

Example `func1IAM.py`:
```python
from troposphereWrapper.iam import *

def get_iam() -> Role:
  helper = RoleBuilderHelper()
  s3FullAccessPolicy = helper.s3FullAccessPolicy()
  pipeAccessPolicy = helper.awsCodePipelineCustomActionAccess()
  logsAccessPolicy = helper.oneClickCreateLogsPolicy()
  return RoleBuilder() \
    .setName("func1IAMRole") \
    .setAssumePolicy(
      helper.defaultAssumeRolePolicyDocument("lambda.amazonaws.com")
      ) \
      .addPolicy(s3FullAccessPolicy) \
      .addPolicy(pipeAccessPolicy) \
      .addPolicy(logsAccessPolicy) \
      .build()
```