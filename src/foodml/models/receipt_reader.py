import base64
import io
import json
import os
import re
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageOps

from llm import call_model


def encode_image(file):
    """Return the receipt photo as a base64 JPEG data URL, small enough for the API."""
    img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")  # apply the phone's rotation
    img.thumbnail((2000, 2000))  # the photo is 24 MP; text stays readable at this size
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def extract_ingredients(file):
    """Read the receipt photo and map every product line to a generic English ingredient with the price of the product."""
    prompt = (
        "This is a photo of a Spanish supermarket receipt (product names are abbreviated). "
        "For EVERY product line, give the generic cooking ingredient in English it refers to "
        "(e.g. 'ACTE.OLIVA V.EXTRA F' -> 'extra virgin olive oil', 'GALLETAS ENERGY' -> 'cookies', "
        "'PAN MASA MADRE' -> 'sourdough bread', 'MAIZ' -> 'corn'). "
        "Also include the price of each product.\n\n"
        "Skip header/footer lines (store info, totals, taxes, payment, dates). "
        "Use null for products that are not food (cleaning, toiletries, bags).\n\n"
        'Reply with JSON: {"items": [{"line": "<product text as printed>", "ingredient": "<ingredient or null>", "price": "<price or null>"}]}'
    )
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": encode_image(file)}},
    ]
    return pd.DataFrame(call_model(content)["items"], columns=["line", "ingredient"])


