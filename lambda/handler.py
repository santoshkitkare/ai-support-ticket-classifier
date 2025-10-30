import os
import json
import uuid
from datetime import datetime
import boto3
from decimal import Decimal
import requests

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('REGION'))
bedrock = boto3.client("bedrock-runtime", region_name="ap-south-1")

table = dynamodb.Table(os.getenv('DDB_TABLE'))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
BEDROCK_MODEL = os.getenv('BEDROCK_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')

SYSTEM_PROMPT = f"""
You are a support ticket classifier. 
Analyze the ticket and return a JSON response with these keys: category, confidence, explanation.
Allowed categories: Network, Billing, Hardware, Software, Account, Other.
Return only valid JSON, nothing else.
Example:
Ticket: "Router light blinking red, no internet"
Response: {{"category": "Network", "confidence": 0.91, "explanation": "Network connectivity failure"}}
"""

def classify_with_openai(text: str) -> dict:
    # prompt = build_prompt(text)
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Ticket: {text}"}],
        "temperature": 0.0,
        "max_tokens": 200,
    }

    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    resp.raise_for_status()
    content = resp.json()['choices'][0]['message']['content']

    try:
        return json.loads(content)
    except:
        return {"category": "Other", "confidence": 0.0, "explanation": content}


def classify_with_bedrock(text: str) -> dict:
    # prompt = build_prompt(text)

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL,
        body=json.dumps({"anthropic_version": "bedrock-2023-05-31",
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": f"Ticket: {text}"}
            ],
            "max_tokens": 200
        }),
        contentType="application/json",
        accept="application/json"
    )

    try:
        print(f"Response : {response}")
        # response is the output from bedrock_runtime.invoke_model(...)
        streaming_body = response['body']

        # Read and decode
        model_output = streaming_body.read().decode("utf-8")
        print(f"Model Output: {model_output}")

        # Parse to dictionary
        result = json.loads(model_output)

        # Now you can safely use 'get' as expected, for example:
        text = json.loads(result.get("content", [{}])[0].get("text", ""))
        print(f"Final Result :{text}")
        return text
    except Exception:
        parsed = {"category": "Other", "confidence": 0.0, "explanation": "Could not parse model response."}


def lambda_handler(event, context):
    print(f"Event: {event}")
    http_methdod = event.get("httpMethod")
    path = event.get("path")
    body = json.loads(event.get("body") or "{}")

    if http_methdod == "POST" and path.endswith("classify"):
        # body = event.get("body") or "{}"
        text = body.get("ticket_text", "").strip()
        model = body.get("model", "openai").strip()
        model_name = OPENAI_MODEL

        if not text:
            return {"statusCode": 400, "body": json.dumps({"error": "ticket_text required"})}
        
        if model == "bedrock":
            result = classify_with_bedrock(text)
            print("Got Return: {result}")
            model_name = BEDROCK_MODEL
        else:
            result = classify_with_openai(text)

        ticket_id = str(uuid.uuid4())
        item = {
            "ticket_id": ticket_id,
            "ticket_text": text,
            "category": result.get("category", "Other"),
            "confidence": Decimal(str(float(result.get("confidence", 0.0)))),
            "explanation": result.get("explanation", ""),
            "model": model_name,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        table.put_item(Item=item)
        return {"statusCode": 200, "body": json.dumps(item, default=str)}
    
    if http_methdod == "GET" and path.endswith("tickets"):
        all_items = []
        response = table.scan()  # Scan returns all items
        items = response.get('Items', [])
        all_items.extend(items)

        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items = response.get('Items', [])
            all_items.extend(items)

        print(f"Total item fetched from DynamoDB table: {len(all_items)}")
        # sort descending by timestamp
        all_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"statusCode": 200, "body": json.dumps(all_items[:20], default=str)}

    return {"statusCode": 404, "body": json.dumps({"error": "Unknown path"})}
