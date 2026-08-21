from flask import Blueprint, jsonify, request
import os
import json
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) 
except ImportError:
    print("[ERROR] Not openai library found")
    OPENAI_AVAILABLE = False

ai_bp = Blueprint("ai_api", __name__)

BASE_PATH = os.getcwd()
TEMPLATE_PATH = os.path.join(BASE_PATH, "data/aisuggestions/context_template_prompt_simplified.json")
DUMMY_RESPONSE_PATH = os.path.join(BASE_PATH, "data/aisuggestions/dummy_rEasype.json")
MODEL="gpt-3.5-turbo" #

@ai_bp.route("/query", methods=["POST"])
def ai_scientist():
    data = request.json or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"ok": False, "response": "No query provided"}), 400
    if OPENAI_AVAILABLE:
        try:

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
            # Modern API call format
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.3
            )

            # Modern dot notation instead of dictionary brackets
            response_text = response.choices[0].message.content

            # Try to parse the JSON output from the model
            try:
                experiment_json = json.loads(response_text)
            except json.JSONDecodeError:
                print(f"[Error]: Model did not return valid JSON. Raw output: {response_text}")
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