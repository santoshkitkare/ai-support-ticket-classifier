variable "region" {
  default = "ap-south-1"
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "openai_model" {
  default = "gpt-4o-mini"
}

variable "bedrock_model" {
  default = "anthropic.claude-3-sonnet-20240229-v1:0"
}
