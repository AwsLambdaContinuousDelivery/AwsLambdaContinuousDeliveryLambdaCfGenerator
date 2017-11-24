# these tests can be run locally if manually provide the ARN
# but should also be run automatically in the staging areas
import boto3
import unittest
import os, sys

arn = ""
stage = ""
class TestStringMethods(unittest.TestCase):
  def test_emptyInvokation_ExceptNot200StatusCode(self):
    client = boto3.client('lambda')
    payload = b""
    response = client.invoke(
      FunctionName = arn,
      InvocationType = RequestResponse,
      LogType = 'Tail',
      Payload = payload
    )
    assertNotEqual(response["StatusCode"], 200)

if __name__ == "__main__":
  if len(sys.argv) < 2:
    raise Exception("No AWS Lambda ARN provided")
  arn = sys.argv[1]
  unittest.main()