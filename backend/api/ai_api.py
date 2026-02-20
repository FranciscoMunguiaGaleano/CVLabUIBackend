from flask import Blueprint, jsonify, request
import os
import json

# Optional OpenAI import
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

ai_bp = Blueprint("ai_api", __name__)

BASE_PATH = os.getcwd()
TEMPLATE_PATH = os.path.join(BASE_PATH, "data/aisuggestions/context_template_prompt.json")
DUMMY_RESPONSE_PATH = os.path.join(BASE_PATH, "data/aisuggestions/dummy_rEasype.json")


@ai_bp.route("/query", methods=["POST"])
def ai_scientist():
    data = request.json or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"ok": False, "response": "No query provided"}), 400

    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if OPENAI_AVAILABLE and openai_api_key:
        try:
            openai.api_key = openai_api_key

            # Load context template
            if os.path.exists(TEMPLATE_PATH):
                with open(TEMPLATE_PATH, "r") as f:
                    template = json.load(f)

                # Inject user query into template
                template["context"]["USER_INPUT_BLOCK"]["USER_REQUIREMENTS"] = query
                system_prompt = json.dumps(template["context"])
            else:
                system_prompt = "You are a CVLab AI Scientist."

            # OpenAI call
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.3
            )

            response_text = response['choices'][0]['message']['content']

            # TODO: parse experiment_json from response_text if your LLM outputs JSON
            experiment_json = _load_dummy_json()

            return jsonify({
                "ok": True,
                "response": response_text,
                "experiment_json": experiment_json,
                "filename": "dummy_rEasype.json"
            })

        except Exception as e:
            error_message = f"⚠️ OpenAI API unavailable or error occurred: {str(e)}. Returning dummy example :3"
            return _return_dummy_response(error_message)

    # No API key: fallback
    fallback_message = "⚠️ No OpenAI API key found. Returning dummy example :3"
    return _return_dummy_response(fallback_message)


def _load_dummy_json():
    """Helper to load dummy JSON"""
    if os.path.exists(DUMMY_RESPONSE_PATH):
        with open(DUMMY_RESPONSE_PATH, "r") as f:
            return json.load(f)
    return {}


def _return_dummy_response(error_message="⚠️ Using dummy response :3"):
    """Return dummy JSON and formatted explanation"""
    experiment_json = _load_dummy_json()

    assumptions_list = experiment_json.get("llm_reasoning", {}).get("assumptions", [])
    assumptions_text = "\n".join(f"- {assumption}" for assumption in assumptions_list)

    explanation = (
        f"{error_message}\n\n"
        f"📊 {experiment_json.get('metadata', {}).get('description', '')}\n\n"
        f"🧪 Name: {experiment_json.get('metadata', {}).get('experiment_name', '')}\n\n"
        f"🎯 Explanation:\n\n"
        f"{experiment_json.get('llm_reasoning', {}).get('selected_mode_explanation','')}\n\n"
        f"{experiment_json.get('llm_reasoning', {}).get('parameter_selection_logic','')}\n\n"
        f"{experiment_json.get('llm_reasoning', {}).get('objective_selection_logic','')}\n\n"
        f"{experiment_json.get('llm_reasoning', {}).get('constraint_validation_summary','')}\n\n"
        f"⚠️ Important assumptions:\n\n"
        f"{assumptions_text}\n\n"
        f"File generated: dummy_rEasype.json\n\n"
        f"➡ To start this experiment, press 'rEasype'."
    )

    return jsonify({
        "ok": True,
        "response": explanation,
        "experiment_json": experiment_json,
        "filename": "dummy_rEasype.json"
    })