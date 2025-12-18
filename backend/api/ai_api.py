from flask import Blueprint, jsonify, request
import time
from transformers import pipeline

generator = pipeline(
    "text-generation",
    model="distilgpt2"
)

ai_bp = Blueprint("ai_api", __name__)

@ai_bp.route("/query", methods=["POST"])
def ai_scientist():
    data = request.json or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({
            "ok": False,
            "response": "No query provided."
        }), 400

    output = generator(
        query,
        max_length=30,
        num_return_sequences=1
    )

    return jsonify({
        "ok": True,
        "response": output[0]["generated_text"]
    })