import os
import json
import google.generativeai as genai

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)


def classify_transactions(batch):

    prompt = f"""
You are a finance transaction classifier.

Classify each transaction into EXACTLY one category:

Food
Shopping
Travel
Transport
Utilities
Cash Withdrawal
Entertainment
Other

Return ONLY a JSON array.

Format:

[
  {{
    "id": 1,
    "category": "Food"
  }}
]

Transactions:

{json.dumps(batch)}
"""

    response = model.generate_content(prompt)

    return response.text

def generate_summary(summary_input):

    prompt = f"""
You are a financial analyst.

Return ONLY valid JSON.

Format:

{{
  "total_spend_inr": 0,
  "total_spend_usd": 0,
  "top_merchants": [],
  "anomaly_count": 0,
  "narrative": "",
  "risk_level": "low"
}}

Input:

{json.dumps(summary_input)}
"""

    response = model.generate_content(prompt)

    return response.text