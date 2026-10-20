import json
import os
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

def call_model(content):
    """Send one user message and parse the model's JSON reply."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    text = response.choices[0].message.content
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)  # drop reasoning if the model includes it
    return json.loads(text[text.find("{"): text.rfind("}") + 1])
