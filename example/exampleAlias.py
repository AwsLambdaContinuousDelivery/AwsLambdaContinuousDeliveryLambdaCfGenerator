from troposphere.awslambda import Alias

alias = "exampleAlias"

def get_alias(arn: str) -> Alias:
  return Alias( alias
              , Description = "Nothing"
              , FunctionName = arn
              , FunctionVersion = "$LATEST"
              , Name = alias )