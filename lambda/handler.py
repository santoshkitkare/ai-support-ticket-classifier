import os
import json
import uuid
from datetime import datetime
import boto3
from decimal import Decimal
import requests

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('REGION'))
table = dynamodb.Table(os.getenv('DDB_TABLE'))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')


def build_prompt(ticket_text: str) -> str:
    return f"""
You are a support ticket classifier. 
Analyze the ticket and return a JSON response with these keys: category, confidence, explanation.
Allowed categories: Network, Billing, Hardware, Software, Account, Other.
Example:
Ticket: "Router light blinking red, no internet"
Response: {{"category": "Network", "confidence": 0.91, "explanation": "Network connectivity failure"}}

Ticket: "{ticket_text}"
"""


def classify_with_openai(prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
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


def lambda_handler(event, context):
    print(f"Event: {event}")
    body = json.loads(event.get("body") or "{}")
    text = body.get("ticket_text", "").strip()

    if not text:
        return {"statusCode": 400, "body": json.dumps({"error": "ticket_text required"})}

    prompt = build_prompt(text)
    result = classify_with_openai(prompt)

    ticket_id = str(uuid.uuid4())
    item = {
        "ticket_id": ticket_id,
        "ticket_text": text,
        "category": result.get("category", "Other"),
        "confidence": Decimal(str(float(result.get("confidence", 0.0)))),
        "explanation": result.get("explanation", ""),
        "model": OPENAI_MODEL,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    table.put_item(Item=item)
    return {"statusCode": 200, "body": json.dumps(item, default=str)}
