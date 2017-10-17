from typing import List
import os
import sys
from troposphere import Template
from troposphere.awslambda import Function
from troposphere.iam import Role
from troposphereWrapper.awslambda import *


class MissingFile(Exception):
  def __init__(self, message):
    self.message = message
  def __str__(self):
    return self.message


def getFileContent(filepath: str) -> List[str]:
  ''' Returns the (striped) filecontent from a file '''
  with open (filepath, "r") as xs:
    content = xs.readlines()
  # content = list(map(lambda x: x.strip(), content))
  return content


def getIAM(path: str, prefix: str) -> Role:
  ''' Returns the get_iam() function in prefixIAM.py '''
  iam_name = prefix + "IAM"
  iam_path = "".join([ path, prefix])
  iam_file = "".join([ iam_path, "/", iam_name, ".py"])
  if os.path.isfile(iam_file):
    # we need to import here the file and call the get_iam() function
    import sys
    sys.path.insert(0, iam_path)
    iam_module = __import__(iam_name)
    return iam_module.get_iam()
  else:
    raise MissingFile("IAM file missing")


def getFunctionCode(path: str, prefix: str) -> List[str]:
  ''' Extracts Source Code from the prefixFunction.py file '''
  func_name = prefix + "Function"
  func_path = "".join([ path, prefix, "/", func_name, ".py"])
  if os.path.isfile(func_path):
    return getFileContent(func_path)
  else:
    raise MissingFile("Function Source Code file missing:" + func_path)


def folders(path: str) -> List[str]:
  ''' Returns all Folders in the paths '''
  xs = os.listdir(path)
  return list(filter(lambda x: os.path.isdir(path + x), xs))


def createFuncTemplate(name: str, code: List[str], iam_role: Role) -> Function:
  ''' Takes the source code and an IAM role and creates a lambda function '''
  return LambdaBuilder() \
    .setName(name) \
    .setHandler(name + "_handler") \
    .setSourceCode(code)\
    .setRole(iam_role) \
    .setRuntime(LambdaRuntime.Python3x) \
    .build()


def addFunction(path: str, name: str, template: Template) -> Template:
  ''' Takes a prefix & adds the lambda function to the template '''
  source_code = getFunctionCode(path, name)
  iam_role = getIAM(path, name)
  template.add_resource(iam_role)
  template.add_resource(createFuncTemplate(name, source_code, iam_role))
  return template

def fillTemplate(path: str, funcs: List[str], template: Template) -> Template:
  for func in funcs:
    template = addFunction(path, func, template)
  return template


if __name__ == "__main__":
  path = sys.argv[1]
  t = Template()
  functions = folders(path)
  t = fillTemplate(path, functions, t)
  print(t.to_json())

