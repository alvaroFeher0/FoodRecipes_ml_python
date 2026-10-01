import pandas as pd
import numpy as np
from PIL import Image, ImageOps
import easyocr
import json
import re
import ollama

MIN_CONF = 0.4  # drop low-confidence boxes (specks, back-side print)
MODEL = "qwen2.5:7b-instruct"


def load_reader():
    """Create the EasyOCR reader (slow, so create once and reuse for every image)."""
    return easyocr.Reader(["es", "en"])


def read_receipt(path, reader):
    """Run OCR on a receipt photo and return its text lines."""
    img = ImageOps.exif_transpose(Image.open(path))  # apply the phone's rotation
    img.thumbnail((2000, 2000))  # the photo is 24 MP; shrinking it makes OCR much faster
    results = reader.readtext(np.array(img))  # list of (box, text, confidence)
    filtered = [r for r in results if r[2] > MIN_CONF]
    return group_lines(filtered)


def group_lines(results):
    """Merge EasyOCR boxes into text lines, ordered top-to-bottom and left-to-right."""
    words = sorted(results, key=lambda r: sum(p[1] for p in r[0]) / 4)
    lines = []
    for box, text, conf in words:
        y_center = sum(p[1] for p in box) / 4
        height = box[2][1] - box[0][1]
        # same line if vertical centers are closer than half a box height
        if lines and abs(y_center - lines[-1]["y"]) < height * 0.5:
            lines[-1]["words"].append((box[0][0], text))
        else:
            lines.append({"y": y_center, "words": [(box[0][0], text)]})
    return [" ".join(t for _, t in sorted(line["words"])) for line in lines]



# receipt header/footer words, not products
SKIP = re.compile(r"precio|unitario|subtotal|total|descuento|importe|cantidad|vendedor|c[oó]digo|descr|fecha|hora", re.I)


def clean_lines(lines):
    """Drop non-product lines and strip prices, quantities and tax letters."""
    out = []
    for line in lines:
        if SKIP.search(line):
            continue
        text = re.sub(r"\b\d+\s*[,.]\s*\d+\b|\b\d+\b|\b[ABC]\b|[^\w\s.%-]", " ", line)
        text = re.sub(r"\s+", " ", text).strip()
        if sum(c.isalpha() for c in text) >= 4:
            out.append(text)
    return out


def extract_ingredients(lines):
    prompt = (
        "Each line below was read by OCR from a Spanish supermarket receipt (abbreviated, with OCR errors). "
        "For EVERY line, give the generic cooking ingredient in English it refers to "
        "(e.g. 'ACTE.OLIVA V.EXTRA F' -> 'extra virgin olive oil', 'GALLETAS ENERGY' -> 'cookies', "
        "'PAN MASA MADRE' -> 'sourdough bread', 'MAIZ' -> 'corn'). "
        "Words may be misspelled or cut off, so guess the most likely food. "
        "Use null ONLY for lines that are clearly not food: brand/promo lines like '2-70% ALBO', "
        "store codes, or random letters.\n\n" + "\n".join(lines)
    )
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"line": {"type": "string"}, "ingredient": {"type": ["string", "null"]}},
                    "required": ["line", "ingredient"],
                },
            }
        },
        "required": ["items"],
    }
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=schema,  # forces valid JSON in this shape
        options={"temperature": 0},
    )
    items = json.loads(response.message.content)["items"]
    return pd.DataFrame(items)


def generate_recipes(ingredients, n=3):
    """Ask the local model for n recipes that mainly use the given ingredients."""
    prompt = (
        f"Suggest {n} recipes that mainly use these ingredients "
        "(you may assume salt, pepper, water and basic spices). "
        "Each recipe should use only the ingredients that make sense together; "
        "skip any that don't fit (e.g. sweets in a savory dish): " + ", ".join(ingredients)
    )
    schema = {
        "type": "object",
        "properties": {
            "recipes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "ingredients": {"type": "array", "items": {"type": "string"}},
                        "steps": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["name", "ingredients", "steps"],
                },
            }
        },
        "required": ["recipes"],
    }
    response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}], format=schema)
    return json.loads(response.message.content)["recipes"]


def pipeline(file):
    lines = read_receipt(file, load_reader()) #"receipts/receipt1.jpeg"
    mapping = extract_ingredients(clean_lines(lines))
    ingredients = sorted(mapping["ingredient"].dropna().str.lower().unique())
    print(ingredients)

    recipes = generate_recipes(ingredients)
    for recipe in recipes:
        print(f"\n## {recipe['name']}")
        for item in recipe["ingredients"]:
            print(f"- {item}")
        for i, step in enumerate(recipe["steps"], 1):
            print(f"{i}. {step}")


