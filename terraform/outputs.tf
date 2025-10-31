output "lambda_function_name" {
  value = aws_lambda_function.ticket_classifier.function_name
}

output "dynamodb_table" {
  value = aws_dynamodb_table.tickets.name
}

output "api_endpoint" {
  value = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${var.region}.amazonaws.com/prod"
}
