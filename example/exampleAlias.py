from troposphere.awslambda import Alias

alias = "exampleAlias"

def get_alias(arn: str, stage: str) -> Alias:
    return Alias( alias + stage
                , Description = "Nothing"
                , FunctionName = arn
                , FunctionVersion = "$LATEST"
                , Name = alias + stage)