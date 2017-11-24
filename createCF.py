from typing import List, Dict
import os
import sys
from troposphere import Template, Output
from troposphere.iam import Role
from troposphere.awslambda import Function, Alias
from troposphereWrapper.awslambda import *

class MissingFile(Exception):
  def __init__(self, message):
    self.message = message
  def __str__(self):
    return self.message


def getFileContent(filepath: str) -> List[str]:
  ''' Returns the filecontent from a file '''
  with open (filepath, "r") as xs:
    content = xs.read().splitlines()
  content = list(map(lambda x: str(x), content))
  return content


def getIAM(path: str, prefix: str) -> Role:
  ''' Returns the get_iam() function in prefixIAM.py '''
  iam_name = prefix + "IAM"
  iam_path = "".join([ path, prefix])
  iam_file = "".join([ iam_path, "/", iam_name, ".py"])
  if os.path.isfile(iam_file):
    # we need to import here the file and call the get_iam() function
    sys.path.insert(0, iam_path)
    iam_module = __import__(iam_name)
    return iam_module.get_iam()
  else:
    raise MissingFile("IAM file missing")


def getEnvVars(path: str, prefix: str) -> dict:
  ''' Returns the Env Vars saved in path/prefixENV.py '''
  env_name = prefix + "ENV"
  env_path = "".join([path, prefix])
  env_file = "".join([env_path, "/", env_name, ".py"])
  if os.path.isfile(env_file):
    sys.path.insert(0, env_path)
    env_module = __import__(env_name)
    return env_module.get_env()
  else:
    return {}


def getFunctionAlias(path: str, prefix: str, arn: str) -> Alias:
  ''' Returns the Alias if present '''
  alias_name = prefix + "Alias"
  alias_path = ''.join([path, prefix])
  alias_file = ''.join([alias_path, "/", alias_name, ".py"])
  if os.path.isfile(alias_file):
    sys.path.insert(0, alias_path)
    alias_module = __import__(alias_name)
    return alias_module.get_alias(arn)
  else:
    return None

def getFunctionCode(path: str, prefix: str) -> List[str]:
  ''' Extracts Source Code from the prefixFunction.py file '''
  func_name = prefix + "Function"
  func_path = "".join([ path, prefix, "/", func_name, ".py"])
  if os.path.isfile(func_path):
    return getFileContent(func_path)
  else:
    raise MissingFile("Function Source Code file missing:" + func_path)


def folders(path: str) -> List[str]:
  ''' Returns all Folders in the paths except the `lambdaCICDBuilder folder'''
  # TODO: Pretty ugly, we should find a better way
  xs = os.listdir(path)
  xs = filter(lambda x: "lambdaCICDBuilder" not in x, xs)
  xs = filter(lambda x: "src" not in x, xs)
  xs = filter(lambda x: x[0] != ".", xs)
  xs = filter(lambda x: os.path.isdir(path + x), xs)
  return list(xs)


def getLambdaBuilder(name: str, code: List[str], role: Role) -> LambdaBuilder:
  ''' Takes the source code and an IAM role and creates a lambda function '''
  return LambdaBuilder() \
    .setName(name) \
    .setHandler("index." + name + "_handler") \
    .setSourceCode(code)\
    .setRole(role) \
    .setRuntime(LambdaRuntime.Python3x)


def addFunction(path: str, name: str, template: Template) -> Template:
  ''' Takes a prefix & adds the lambda function to the template '''
  source_code = getFunctionCode(path, name)
  iam_role = getIAM(path, name)
  template.add_resource(iam_role)
  func = getLambdaBuilder(name, source_code, iam_role)
  for key, value in getEnvVars(path, name).items():
    func = func.addEnvironmentVariable(key, value )
  func_ref = template.add_resource(func.build())
  alias = getFunctionAlias(path, name, GetAtt(func_ref, "Arn"))
  if alias is not None:
    template.add_resource(alias)
  template.add_output([
      Output( name + "ARN"
            , Value = GetAtt(func_ref, "Arn")
            , Description = "ARN for Lambda Function"
            )])
  return template


def fillTemplate(path: str, funcs: List[str], template: Template) -> Template:
  for func in funcs:
    template = addFunction(path, func, template)
  return template


def getTemplateFromFolder(path: str) -> Template:
  ''' Transforms a folder with Lambdas into a CF Template '''
  t = Template()
  functions = folders(path)
  t = fillTemplate(path, functions, t)
  return t


if __name__ == "__main__":
  # print ("using python version: " + sys.version)
  if len(sys.argv) < 2:
    print("Error: Need the path of the folder with the functions")
    sys.exit(1)
  path = sys.argv[1]
  t = getTemplateFromFolder(path)
  print(t.to_json())
