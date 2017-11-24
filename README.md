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
      - python3 lambdaCICDBuilder/createCF.py --path $(pwd)/ --stage "Alpha" >> alpha-stack.json
artifacts:
  files:
    - alpha-stack.json
```


## Folder structure of Lambda Functions

It is important that your functions have the following naming:
- Each function must be in an own folder which bears the name of the function starting with a lower case character
- Each function folder must consists of two `python` files, which start with the name of the function (== foldername) appended with `Function.py` and `IAM.py` respectively
- `{$name}Function.py` must consists the handler function, which has the naming structure `{$name}_handler(event, context)`
- `{$name}IAM.py` must contain a function `get_IAM(stage: str) -> Role` which returns a `troposphere.iam.Role`
- If you need, you can also provide environment variables to the lambda function by adding a `{$name}ENV.py` file containing a `get_env(stage: str) -> dict` function returning a dictionary of key, values. This file is optional
- Alias are also supported by simply adding a `{$name}Alias.py` file containing a `get_alias(arn: str, stage: str) -> Alias` function

```
example
| exampleFunction.py
| exampleIAM.py
| exampleENV.py
| exampleAlias.py
func2
| func2Function.py
| func2IAM.py
```

## Example

`example/exampleFunction.py`
```python
from typing import List

def example_handler(event, context):
  return 0
```

`example/exampleIAM.py`
```python
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
```

`example/exampleENV.py`
```python
def get_env(stage: str) -> dict:
  return { "hello" : "world" }
```

`example/exampleAlias.py`
```python
from troposphere.awslambda import Alias

def get_alias(arn: str, stage: str) -> Alias:
  return Alias( alias + stage
              , Description = "Nothing"
              , FunctionName = arn
              , FunctionVersion = "$LATEST"
              , Name = "exampleAlias" + stage )
```


These files yield the following CloudFormation `json` template
```json
{
    "Outputs": {
        "exampleARN": {
            "Description": "ARN for Lambda Function",
            "Value": {
                "Fn::GetAtt": [
                    "example",
                    "Arn"
                ]
            }
        }
    },
    "Resources": {
        "example": {
            "Properties": {
                "Code": {
                    "ZipFile": {
                        "Fn::Join": [
                            "\n",
                            [
                                "from typing import List",
                                "",
                                "def example_handler(event, context):",
                                "  return 0"
                            ]
                        ]
                    }
                },
                "Environment": {
                    "Variables": {
                        "hello": "world"
                    }
                },
                "FunctionName": {
                    "Fn::Sub": "example${AWS::StackName}"
                },
                "Handler": "index.example_handler",
                "MemorySize": 128,
                "Role": {
                    "Fn::GetAtt": [
                        "exampleIAMRole",
                        "Arn"
                    ]
                },
                "Runtime": "python3.6"
            },
            "Type": "AWS::Lambda::Function"
        },
        "exampleAlias": {
            "Properties": {
                "Description": "Nothing",
                "FunctionName": {
                    "Fn::GetAtt": [
                        "example",
                        "ARN"
                    ]
                },
                "FunctionVersion": "$LATEST",
                "Name": "exampleAlias"
            },
            "Type": "AWS::Lambda::Alias"
        },
        "exampleIAMRole": {
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "sts:AssumeRole"
                            ],
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "lambda.amazonaws.com"
                            }
                        }
                    ]
                },
                "Policies": [
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "s3:*"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "*"
                                    ]
                                }
                            ]
                        },
                        "PolicyName": {
                            "Fn::Sub": "S3FullAccessPolicy-${AWS::StackName}"
                        }
                    },
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "codepipeline:AcknowledgeJob",
                                        "codepipeline:GetJobDetails",
                                        "codepipeline:PollForJobs",
                                        "codepipeline:PutJobFailureResult",
                                        "codepipeline:PutJobSuccessResult"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "*"
                                    ]
                                }
                            ]
                        },
                        "PolicyName": {
                            "Fn::Sub": "AWSCodePipelineCustomActionAccess-${AWS::StackName}"
                        }
                    },
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "logs:CreateLogGroup",
                                        "logs:CreateLogStream",
                                        "logs:PutLogEvents"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "arn:aws:logs:*:*:*"
                                    ]
                                }
                            ]
                        },
                        "PolicyName": {
                            "Fn::Sub": "OneClickCreateLogsPolicy-${AWS::StackName}"
                        }
                    }
                ],
                "RoleName": {
                    "Fn::Sub": "exampleIAMRole-${AWS::StackName}"
                }
            },
            "Type": "AWS::IAM::Role"
        }
    }
}
{
    "Outputs": {
        "exampleARN": {
            "Description": "ARN for Lambda Function",
            "Value": {
                "Fn::GetAtt": [
                    "exampleAlpha",
                    "Arn"
                ]
            }
        }
    },
    "Resources": {
        "exampleAlias": {
            "Properties": {
                "Description": "Nothing",
                "FunctionName": {
                    "Fn::GetAtt": [
                        "exampleAlpha",
                        "Arn"
                    ]
                },
                "FunctionVersion": "$LATEST",
                "Name": "exampleAlias"
            },
            "Type": "AWS::Lambda::Alias"
        },
        "exampleAlpha": {
            "Properties": {
                "Code": {
                    "ZipFile": {
                        "Fn::Join": [
                            "\n",
                            [
                                "from typing import List",
                                "",
                                "def example_handler(event, context):",
                                "  return 0"
                            ]
                        ]
                    }
                },
                "Environment": {
                    "Variables": {
                        "hello": "world"
                    }
                },
                "FunctionName": {
                    "Fn::Sub": "exampleAlpha${AWS::StackName}"
                },
                "Handler": "index.example_handler",
                "MemorySize": 128,
                "Role": {
                    "Fn::GetAtt": [
                        "exampleIAMRole",
                        "Arn"
                    ]
                },
                "Runtime": "python3.6"
            },
            "Type": "AWS::Lambda::Function"
        },
        "exampleIAMRole": {
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "sts:AssumeRole"
                            ],
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "lambda.amazonaws.com"
                            }
                        }
                    ]
                },
                "Policies": [
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "s3:*"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "*"
                                    ]
                                }
                            ]
                        },
                        "PolicyName": {
                            "Fn::Sub": "S3FullAccessPolicy-${AWS::StackName}"
                        }
                    },
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "codepipeline:AcknowledgeJob",
                                        "codepipeline:GetJobDetails",
                                        "codepipeline:PollForJobs",
                                        "codepipeline:PutJobFailureResult",
                                        "codepipeline:PutJobSuccessResult"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "*"
                                    ]
                                }
                            ]
                        },
                        "PolicyName": {
                            "Fn::Sub": "AWSCodePipelineCustomActionAccess-${AWS::StackName}"
                        }
                    },
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "logs:CreateLogGroup",
                                        "logs:CreateLogStream",
                                        "logs:PutLogEvents"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "arn:aws:logs:*:*:*"
                                    ]
                                }
                            ]
                        },
                        "PolicyName": {
                            "Fn::Sub": "OneClickCreateLogsPolicy-${AWS::StackName}"
                        }
                    }
                ],
                "RoleName": {
                    "Fn::Sub": "exampleIAMRole-${AWS::StackName}"
                }
            },
            "Type": "AWS::IAM::Role"
        }
    }
}
Alpha
{
    "Outputs": {
        "exampleARN": {
            "Description": "ARN for Lambda Function",
            "Value": {
                "Fn::GetAtt": [
                    "exampleAlpha",
                    "Arn"
                ]
            }
        }
    },
    "Resources": {
        "exampleAliasAlpha": {
            "Properties": {
                "Description": "Nothing",
                "FunctionName": {
                    "Fn::GetAtt": [
                        "exampleAlpha",
                        "Arn"
                    ]
                },
                "FunctionVersion": "$LATEST",
                "Name": "exampleAliasAlpha"
            },
            "Type": "AWS::Lambda::Alias"
        },
        "exampleAlpha": {
            "Properties": {
                "Code": {
                    "ZipFile": {
                        "Fn::Join": [
                            "\n",
                            [
                                "from typing import List",
                                "",
                                "def example_handler(event, context):",
                                "  return 0"
                            ]
                        ]
                    }
                },
                "Environment": {
                    "Variables": {
                        "hello": "world"
                    }
                },
                "FunctionName": {
                    "Fn::Sub": "exampleAlpha${AWS::StackName}"
                },
                "Handler": "index.example_handler",
                "MemorySize": 128,
                "Role": {
                    "Fn::GetAtt": [
                        "exampleIAMRoleAlpha",
                        "Arn"
                    ]
                },
                "Runtime": "python3.6"
            },
            "Type": "AWS::Lambda::Function"
        },
        "exampleIAMRoleAlpha": {
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "sts:AssumeRole"
                            ],
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "lambda.amazonaws.com"
                            }
                        }
                    ]
                },
                "Policies": [
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "s3:*"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "*"
                                    ]
                                }
                            ]
                        },
                        "PolicyName": {
                            "Fn::Sub": "S3FullAccessPolicy-${AWS::StackName}"
                        }
                    },
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "codepipeline:AcknowledgeJob",
                                        "codepipeline:GetJobDetails",
                                        "codepipeline:PollForJobs",
                                        "codepipeline:PutJobFailureResult",
                                        "codepipeline:PutJobSuccessResult"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "*"
                                    ]
                                }
                            ]
                        },
                        "PolicyName": {
                            "Fn::Sub": "AWSCodePipelineCustomActionAccess-${AWS::StackName}"
                        }
                    },
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "logs:CreateLogGroup",
                                        "logs:CreateLogStream",
                                        "logs:PutLogEvents"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                        "arn:aws:logs:*:*:*"
                                    ]
                                }
                            ]
                        },
                        "PolicyName": {
                            "Fn::Sub": "OneClickCreateLogsPolicy-${AWS::StackName}"
                        }
                    }
                ],
                "RoleName": {
                    "Fn::Sub": "exampleIAMRoleAlpha-${AWS::StackName}"
                }
            },
            "Type": "AWS::IAM::Role"
        }
    }
}


```