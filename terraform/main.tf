terraform {
  backend "s3" {
    bucket         = "santosh-s3-bucket-demo"
    key            = "terraform_states/ai-support-ticket-classifier/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  required_version = ">= 1.5.0"
}

provider "aws" {
  region = var.region
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "ticket_classifier_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "ddb_full_access" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

# DynamoDB Table
resource "aws_dynamodb_table" "tickets" {
  name         = "TicketClassificationTable"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ticket_id"

  attribute {
    name = "ticket_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "CreatedAtIndex"
    hash_key        = "created_at"
    projection_type = "ALL"
  }
}

# Lambda Function
resource "aws_lambda_function" "ticket_classifier" {
  function_name = "ticket_classifier_lambda"
  role          = aws_iam_role.lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  # Load Lambda dev package from S3
  s3_bucket = "santosh-s3-bucket-demo"
  s3_key    = "lambda_function/AiSupportTicketClassifire.zip"

  environment {
    variables = {
      BEDROCK_MODEL  = var.bedrock_model
      OPENAI_API_KEY = var.openai_api_key
      OPENAI_MODEL   = var.openai_model
      REGION         = var.region
      TABLE_NAME     = aws_dynamodb_table.tickets.name
    }
  }
}

# API Gateway
resource "aws_api_gateway_rest_api" "api" {
  name        = "TicketClassifierAPI"
  description = "API for classifying and fetching support tickets"
}

# /classify Resource
resource "aws_api_gateway_resource" "classify" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "classify"
}

# /tickets Resource
resource "aws_api_gateway_resource" "tickets" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "tickets"
}

# POST /classify Method
resource "aws_api_gateway_method" "classify_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.classify.id
  http_method   = "POST"
  authorization = "NONE"
}

# GET /tickets Method
resource "aws_api_gateway_method" "tickets_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.tickets.id
  http_method   = "GET"
  authorization = "NONE"
}

# Lambda Integration
resource "aws_api_gateway_integration" "classify_integration" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.classify.id
  http_method             = aws_api_gateway_method.classify_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ticket_classifier.invoke_arn
}

resource "aws_api_gateway_integration" "tickets_integration" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.tickets.id
  http_method             = aws_api_gateway_method.tickets_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ticket_classifier.invoke_arn
}

# Lambda Invoke Permission
resource "aws_lambda_permission" "api_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ticket_classifier.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# Deployment
resource "aws_api_gateway_deployment" "deployment" {
  depends_on = [
    aws_api_gateway_integration.classify_integration,
    aws_api_gateway_integration.tickets_integration
  ]
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = "prod"
}

output "api_url" {
  value = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${var.region}.amazonaws.com/prod"
}
