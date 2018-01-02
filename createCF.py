from typing import List, Dict, Tuple
import os
import sys
from troposphere import Template, Output, Export, GetAtt, Join, Ref, Parameter
from troposphere.iam import Role
from troposphere.awslambda import Function, Alias, Environment, Code

import argparse
import re
import yaml

regex = re.compile('[^a-zA-Z0-9]')
S3 = str
Key = str
Source = Tuple[S3, Key]

def loadConfig(path: str) -> dict:
  config = {}
  with open (path + "config/config.yaml", "r") as c:
    config = yaml.load(c)
  if not config:
    raise Exception("Empty config")
  return config


def toAlphanum(s: str) -> str:
  return regex.sub('', s)

class MissingFile(Exception):
  def __init__(self, message):
    self.message = message
  def __str__(self):
    return self.message


def getIAM(path: str, prefix: str, stackname: str, stage: str) -> Role:
  ''' Returns the get_iam() function in config/stage/iam.py '''
  iam_name = "iam"
  iam_path = "".join([ path, "config/", stage])
  iam_file = "".join([ iam_path, "/", iam_name, ".py"])
  if os.path.isfile(iam_file):
    # we need to import here the file and call the get_iam() function
    sys.path.insert(0, iam_path)
    iam_module = __import__(iam_name)
    ref_name = toAlphanum("".join([prefix, stackname, stage]))
    return iam_module.get_iam(ref_name + "IAM")
  else:
    raise MissingFile("IAM file missing:" + iam_file)


def getEnvVars(path: str, prefix: str, stage: str) -> dict:
  ''' Returns the Env Vars saved in config/stage/envVars.py '''
  env_name = "env"
  env_path = "".join([path, "config/", stage])
  env_file = "".join([env_path, "/", env_name, ".py"])
  if os.path.isfile(env_file):
    sys.path.insert(0, env_path)
    env_module = __import__(env_name)
    env = env_module.get_env()
    return env_module.get_env()
  else:
    return {}


def getFunctionAlias( path: str
                    , prefix: str
                    , arn: str
                    , stackname: str
                    , stage: str
                    ) -> Alias:
  ''' Returns the Alias if present '''
  name = "".join([prefix, stackname, stage])

  return Alias( toAlphanum(name) + "Alias"
              , Description = "Automatic Generated Alias"
              , FunctionName = arn
              , FunctionVersion = "$LATEST"
              , Name = name
              )


def folders(path: str) -> List[str]:
  ''' Returns all Folders in the paths except the `lambdaCICDBuilder folder'''
  # TODO: Pretty ugly, we should find a better way
  xs = os.listdir(path)
  xs = filter(lambda x: x[0] != ".", xs)
  xs = filter(lambda x: os.path.isdir(path + x), xs)
  return list(xs)


def getLambda( name: str
             , src: Source
             , role: Role
             , stack: str
             , stage: str
             , env_vars: dict
             , config: dict
             ) -> Function:
  ''' Takes the source code and an IAM role and creates a lambda function '''
  code = Code( S3Bucket = src[0] 
             , S3Key = src[1]
             )
  func_name = "".join([name, stack, stage])
  env_vars = Environment( Variables = env_vars )
  memory = 128
  if "MemorySize" in config:
    memory = config["MemorySize"]
  timeout = 60
  if "Timeout" in config:
    timeout = config["Timeout"]
  
  return Function( toAlphanum(name)
                 , FunctionName = func_name
                 , Handler = config["Handler"]
                 , Code = code
                 , Role = GetAtt(role, "Arn")
                 , Runtime = "python3.6"
                 , Environment = env_vars
                 , MemorySize = memory
                 , Timeout = timeout
                 )


def addFunction( path: str
               , template: Template
               , stackname: str
               , stage: str
               , src: Source
               ) -> Template:
  ''' Takes a prefix & adds the lambda function to the template '''
  config = loadConfig(path)
  name = config["Name"]
  iam_role = getIAM(path, name, stackname, stage)
  template.add_resource(iam_role)
  env_vars = {}
  for key, value in getEnvVars(path, name, stage).items():
    env_vars[key] = value
  func = getLambda(name, src, iam_role, stackname, stage, env_vars, config)
  func_ref = template.add_resource(func)
  alias = getFunctionAlias(path, name, GetAtt(func_ref,"Arn"), stackname, stage)
  if alias is not None:
    template.add_resource(alias)
  template.add_output([
      Output( toAlphanum(name + stackname + stage)
            , Value = GetAtt(func_ref, "Arn")
            , Export = Export(name + stackname + stage)
            , Description = stage +": ARN for Lambda Function"
            )])
  return template


def getTemplate( path: str
               , stackname: str
               , stage: str
               ) -> Template:
  ''' Transforms a folder with Lambdas into a CF Template '''
  t = Template()
  src_key = t.add_parameter(
    Parameter( "S3Key"
             , Type = "String"
             , Description = "S3Key"
             )
    )
  src_s3 = t.add_parameter(
    Parameter( "S3Storage"
             , Type = "String"
             , Description = "S3Storage"
             )
    )
  src = (Ref(src_s3), Ref(src_key))
  t = addFunction(path, t, stackname, stage, src)
  return t

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-p", "--path", help="Path of the folder with the source-code of the aws lambda functions", required = True)
  parser.add_argument("--stage", help="Name of the stage", type = str, required = True)
  parser.add_argument("--stack", help="Name of the stack", type = str, required = True)
  args = parser.parse_args()
  t = getTemplate(args.path, args.stack, args.stage)
  print(t.to_json())