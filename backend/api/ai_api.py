from flask import Blueprint, jsonify, request
import os
import json
import re
import subprocess
import sys
import traceback

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except ImportError:
    print("[ERROR] OpenAI library not found")
    OPENAI_AVAILABLE = False
    client = None
ai_bp = Blueprint("ai_api", __name__)

# ============================================================
# PATHS
# ============================================================
BASE_PATH = os.getcwd()
AISUGGESTIONS_PATH = os.path.join(BASE_PATH,"data","aisuggestions")
TEMPLATE_PATH = os.path.join(AISUGGESTIONS_PATH,"context_template_prompt_simplified.json")
DUMMY_RESPONSE_PATH = os.path.join(AISUGGESTIONS_PATH,"dummy_rEasype.json")
EXPERIMENTS_PATH = os.path.join(AISUGGESTIONS_PATH,"experiments")
os.makedirs(EXPERIMENTS_PATH,exist_ok=True)
# ============================================================
# OPENAI
# ============================================================
MODELS = {"mini": "gpt-5.4-mini","luna": "gpt-5.6-luna","terra": "gpt-5.6-terra"}
CURRENT_MODEL_KEY= "mini"
MODEL = MODELS[CURRENT_MODEL_KEY]

# ============================================================
# EXPERIMENT VALIDATION
# ============================================================
def _validate_experiment(experiment):
    errors = []
    if not isinstance(experiment, dict):
        return ["Experiment must be a JSON object."]
    # ========================================================
    # EXPERIMENT MODE
    # ========================================================
    allowed_modes = ["analite_in_electrolite", "analite_on_working_electrode"]
    mode = experiment.get("experiment_mode")
    if mode not in allowed_modes:
        errors.append("experiment_mode must be either 'analite_in_electrolite' or 'analite_on_working_electrode'.")
    # ========================================================
    # METADATA
    #========================================================
    metadata = experiment.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata must be a JSON object.")
    else:
        if not metadata.get("experiment_name"):
            errors.append("metadata.experiment_name is required.")
        if not metadata.get("experimenter"):
            errors.append("metadata.experimenter is required.")
    # ========================================================
    # NUM SAMPLES
    # ========================================================
    num_samples = experiment.get("num_samples")
    if num_samples is not None:
        if isinstance(num_samples, bool) or not isinstance(num_samples, int):
            errors.append("num_samples must be an integer.")
        elif num_samples < 1:
            errors.append("num_samples must be at least 1.")
        elif num_samples > 31:
            errors.append("num_samples cannot exceed 31.")
    # ========================================================
    # PARALLEL SLOTS
    # =======================================================
    parallel_slots = experiment.get("parallel_echem_slots")
    platform_checklist = experiment.get("platform_checklist", {})
    if isinstance(platform_checklist, dict):
        checklist_slots = platform_checklist.get("parallel_echem_slots_used")
        if checklist_slots is not None:
            if isinstance(checklist_slots, bool) or not isinstance(checklist_slots, int):
                errors.append("platform_checklist.parallel_echem_slots_used must be an integer.")
            elif checklist_slots < 1:
                errors.append("Parallel electrochemistry slots must be at least 1.")
            elif checklist_slots > 3:
                errors.append("Parallel electrochemistry slots cannot exceed 3.")
    if parallel_slots is not None:
        if isinstance(parallel_slots, bool) or not isinstance(parallel_slots, int):
            errors.append("parallel_echem_slots must be an integer.")
        elif parallel_slots < 1:
            errors.append("parallel_echem_slots must be at least 1.")
        elif parallel_slots > 3:
            errors.append("parallel_echem_slots cannot exceed 3.")
    # ========================================================
    # RECIPE
    # ========================================================
    recipe = experiment.get("recipe")
    if not isinstance(recipe, dict):
        errors.append("recipe must be a JSON object.")
        return errors
    # ========================================================
    # SOLIDS
    # ========================================================
    solids = recipe.get("solids", [])
    if not isinstance(solids, list):
        errors.append("recipe.solids must be an array.")
    else:
        if len(solids) > 8:
            errors.append("A maximum of 8 solid cartridges can be used.")
        cartridge_positions = set()
        for index, solid in enumerate(solids):
            prefix = f"Solid {index + 1}"
            if not isinstance(solid, dict):
                errors.append(f"{prefix} must be an object.")
                continue
            # Name
            if not solid.get("name"):
                errors.append(f"{prefix}: name is required.")
            # Role
            if not solid.get("role"):
                errors.append(f"{prefix}: role is required.")
            # Cartridge
            cartridge = solid.get("cartridge_position")
            if cartridge is None:
                errors.append(f"{prefix}: cartridge_position is required.")
            else:
                try:
                    cartridge = int(cartridge)
                    if not 1 <= cartridge <= 8:
                        errors.append(f"{prefix}: cartridge_position must be between 1 and 8.")
                    elif cartridge in cartridge_positions:
                        errors.append(f"{prefix}: cartridge_position {cartridge} is used more than once.")
                    else:
                        cartridge_positions.add(cartridge)
                except (TypeError, ValueError):
                    errors.append(f"{prefix}: cartridge_position must be an integer.")
            # Mass
            mass = solid.get("mass_mg")
            if mass is None:
                errors.append(f"{prefix}: mass_mg is required.")
            else:
                try:
                    mass = float(mass)
                    if mass <= 0:
                        errors.append(f"{prefix}: mass_mg must be greater than 0.")
                    elif mass > 200:
                        errors.append(f"{prefix}: mass_mg cannot exceed 200 mg.")
                except (TypeError, ValueError):
                    errors.append(f"{prefix}: mass_mg must be a number.")

            # Molecular weight
            mw = solid.get("molecular_weight_g_mol")
            if mw is None:
                errors.append(f"{prefix}: molecular_weight_g_mol is required.")
            else:
                try:
                    if float(mw) <= 0:
                        errors.append(f"{prefix}: molecular_weight_g_mol must be greater than 0.")
                except (TypeError, ValueError):
                    errors.append(f"{prefix}: molecular_weight_g_mol must be a number.")
    # ========================================================
    # LIQUIDS
    # ========================================================
    liquids = recipe.get("liquids", [])
    if not isinstance(liquids, list):
        errors.append("recipe.liquids must be an array.")
    else:
        if len(liquids) > 4:
            errors.append("A maximum of 4 liquid channels can be used.")
        channels = set()
        for index, liquid in enumerate(liquids):
            prefix = f"Liquid {index + 1}"
            if not isinstance(liquid, dict):
                errors.append(f"{prefix} must be an object.")
                continue
            if not liquid.get("name"):
                errors.append(f"{prefix}: name is required.")

            channel = liquid.get("channel")
            if channel is None:
                errors.append(f"{prefix}: channel is required.")
            else:
                try:
                    channel = int(channel)
                    if not 1 <= channel <= 4:
                        errors.append(f"{prefix}: channel must be between 1 and 4.")
                    elif channel in channels:
                        errors.append(f"{prefix}: channel {channel} is used more than once.")
                    else:
                        channels.add(channel)
                except (TypeError, ValueError):
                    errors.append(f"{prefix}: channel must be an integer.")

            volume = liquid.get("volume_ml")
            if volume is None:
                errors.append(f"{prefix}: volume_ml is required.")
            else:
                try:
                    if float(volume) <= 0:
                        errors.append(f"{prefix}: volume_ml must be greater than 0.")
                except (TypeError, ValueError):
                    errors.append(f"{prefix}: volume_ml must be a number.")
    # ========================================================
    # FINAL VOLUME
    # ========================================================
    final_volume = recipe.get("final_volume_ml")
    if final_volume is None:
        errors.append("recipe.final_volume_ml is required.")
    else:
        try:
            final_volume = float(final_volume)
            if final_volume <= 0:
                errors.append("final_volume_ml must be greater than 0.")
            elif final_volume > 10:
                errors.append("final_volume_ml cannot exceed 10 mL.")
        except (TypeError, ValueError):
            errors.append("final_volume_ml must be a number.")
    # ========================================================
    # TOTAL LIQUID VOLUME
    # ========================================================
    if isinstance(liquids, list) and final_volume:
        try:
            total_liquid_volume = sum(float(liquid.get("volume_ml", 0)) for liquid in liquids if isinstance(liquid, dict))
            if abs(total_liquid_volume - float(final_volume)) > 0.0001:
                errors.append(f"Total liquid volume ({total_liquid_volume} mL) does not match final_volume_ml ({final_volume} mL).")
        except (TypeError, ValueError):
            pass
    # ========================================================
    # PLATFORM CHECKLIST
    # ========================================================
    if not isinstance(platform_checklist, dict):
        errors.append("platform_checklist must be a JSON object.")
    else:
        vials = platform_checklist.get("experiment_vials_required_per_batch")
        if vials is not None:
            try:
                vials = int(vials)
                if vials < 1:
                    errors.append("experiment_vials_required_per_batch must be at least 1.")
                elif vials > 31:
                    errors.append("experiment_vials_required_per_batch cannot exceed 31.")
            except (TypeError, ValueError):
                errors.append("experiment_vials_required_per_batch must be an integer.")
    return errors
# ============================================================
# SAFE FILENAME
# ============================================================
def _safe_filename(filename):
    if not filename:
        filename = "rEasype_experiment"
    filename = os.path.basename(str(filename))
    if filename.lower().endswith(".json"):
        filename = filename[:-5]
    filename = re.sub(r"[^a-zA-Z0-9_.-]","_",filename)
    if not filename:
        filename = "rEasype_experiment"
    return f"{filename}.json"
# ============================================================
# PARSE MODEL JSON
# ============================================================
def _parse_model_json(response_text):
    if not response_text:
        return None
    text = response_text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*","",text,flags=re.IGNORECASE)
        text = re.sub(r"\s*```$","",text)
        text = text.strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    return None
# ============================================================
# LOAD DUMMY JSON
# ============================================================
def _load_dummy_json():
    if not os.path.exists(DUMMY_RESPONSE_PATH):
        return {}
    try:
        with open(DUMMY_RESPONSE_PATH,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not load dummy JSON: {e}")
        return {}
# ============================================================
# FORMAT AI RESPONSE
# ============================================================
def _format_experiment_response(experiment_json):
    metadata = experiment_json.get("metadata",{})
    reasoning = experiment_json.get("llm_reasoning",{})
    recipe = experiment_json.get("recipe",{})
    cv = experiment_json.get("cv_parameters",{})
    experiment_name = metadata.get("experiment_name","Unnamed experiment")
    description = metadata.get("description","")
    mode = experiment_json.get("experiment_mode","")
    num_samples = experiment_json.get("num_samples",recipe.get("num_samples",))
    # ========================================================
    # MATERIALS
    # ========================================================
    solids = recipe.get("solids",[])
    if solids:
        solids_text = "\n".join(f"- {solid.get('name', 'Unknown')} ({solid.get('mass_mg', 'N/A')} mg)" for solid in solids)
    else:
        solids_text = "- None"
    liquids = recipe.get("liquids", [])
    if liquids:
        liquids_text = "\n".join(f"- {liquid.get('name', 'Unknown')} ({liquid.get('volume_ml', 'N/A')} mL)" for liquid in liquids)
    else:
        liquids_text = "- None"
    # ========================================================
    # CV PARAMETERS
    # ========================================================
    potential_window = cv.get("potential_window")
    if (isinstance(potential_window, list) and len(potential_window) >= 2):
        potential_text = (f"{potential_window[0]} V → {potential_window[1]} V")
    else:
        potential_text = "Not specified"
    scan_rate = cv.get("scan_rate_v_s")
    step_size = cv.get("step_size_v")
    cycles = cv.get("cycles")
    working_electrode = cv.get("working_electrode_type")
    counter_electrode = cv.get("counter_electrode_type")
    reference_electrode = cv.get("reference_electrode")
    polishing = cv.get("polishing")
    polishing_cycles = cv.get("polishing_cycles")
    # ========================================================
    # RECIPE
    # ========================================================
    final_volume = recipe.get("final_volume_ml")
    mixing_method = recipe.get("mixing_method")
    mixing_time = recipe.get("mixing_time_seconds")
    purge = recipe.get("purge")
    # ========================================================
    # REASONING
    # ========================================================
    mode_explanation = reasoning.get("selected_mode_explanation","")
    parameter_logic = reasoning.get("parameter_selection_logic","")
    assumptions = reasoning.get("assumptions",[])
    assumptions_text = "\n".join(f"- {assumption}" for assumption in assumptions)
    # ========================================================
    # BUILD RESPONSE
    # ========================================================
    response = (
        f"🧪 Experiment: {experiment_name}\n\n"

        f"📊 {description}\n\n"

        f"🔬 Mode: {mode}\n"
        f"Samples: {num_samples}\n\n"

        f"⚗️ Materials\n"
        f"Solids:\n"
        f"{solids_text}\n\n"

        f"Liquids:\n"
        f"{liquids_text}\n\n"

        f"🧪 Preparation\n"
        f"Final volume: {final_volume} mL\n"
        f"Mixing: {mixing_method} "
        f"({mixing_time} s)\n"
        f"Purge: {'Yes' if purge else 'No'}\n\n"

        f"⚡ CV Parameters\n"
        f"Working electrode: {working_electrode}\n"
        f"Reference electrode: {reference_electrode}\n"
        f"Counter electrode: {counter_electrode}\n"
        f"Potential window: {potential_text}\n"
        f"Scan rate: {scan_rate} V/s\n"
        f"Step size: {step_size} V\n"
        f"Cycles: {cycles}\n"
        f"Electrode polishing: "
        f"{'Yes' if polishing else 'No'}")
    if polishing:
        response += (f" ({polishing_cycles} cycles)")
    response += (
        f"\n\n🧠 Selection rationale\n{mode_explanation}\n\n{parameter_logic}")
    if assumptions_text:
        response += (f"\n\n⚠️ Important assumptions:\n {assumptions_text}")
    response += ("\n\n➡ The complete experiment configuration is ready for rEasype.")
    return response
# ============================================================
# DUMMY RESPONSE
# ============================================================
def _return_dummy_response(error_message="⚠️ Using dummy response :3"):
    experiment_json = _load_dummy_json()
    assumptions_list = (
        experiment_json.get("llm_reasoning", {}).get("assumptions", []))
    assumptions_text = "\n".join(f"- {assumption}" for assumption in assumptions_list)
    explanation = (
        f"{error_message}\n\n"
        f"📊 "
        f"{experiment_json.get('metadata', {}).get('description', '')}"
        f"\n\n"
        f"🧪 Name: "
        f"{experiment_json.get('metadata', {}).get('experiment_name', '')}"
        f"\n\n"
        f"🎯 Explanation:\n\n"
        f"{experiment_json.get('llm_reasoning', {}).get('selected_mode_explanation', '')}"
        f"\n\n"
        f"{experiment_json.get('llm_reasoning', {}).get('parameter_selection_logic', '')}"
        f"\n\n"
        f"{experiment_json.get('llm_reasoning', {}).get('objective_selection_logic', '')}"
        f"\n\n"
        f"{experiment_json.get('llm_reasoning', {}).get('constraint_validation_summary', '')}"
        f"\n\n"
        f"⚠️ Important assumptions:\n\n"
        f"{assumptions_text}"
        f"\n\n"
        f"➡ To start this experiment, press 'rEasype'."
    )
    return jsonify({"ok": True,"response": explanation,"experiment_json": experiment_json,"filename": "dummy_rEasype.json"})

# ============================================================
# BASIC ENDPOINT TEST
# ============================================================

@ai_bp.route("/health", methods=["GET"])
def ai_health():
    return jsonify({"ok": True,"service": "ai_scientist","message": "AI Scientist API is reachable."})

@ai_bp.route("/ping", methods=["GET"])
def ai_ping():
    print("\n[rEasype] >>> PING ENDPOINT HIT <<<")
    return jsonify({"ok": True,"service": "ai_scientist","message": "AI Scientist API ping successful."})

# ============================================================
# AI QUERY
# ============================================================

@ai_bp.route("/query", methods=["POST"])
def ai_scientist():
    try:
        data = request.get_json(silent=True) or {}
        query = data.get("query","").strip()
        if not query:
            return jsonify({"ok": False,"response": "No query provided."}), 400

        if not OPENAI_AVAILABLE:
            return _return_dummy_response("⚠️ OpenAI library unavailable. ""Returning dummy example.")
        # ----------------------------------------------------
        # Load context template
        # ----------------------------------------------------
        if os.path.exists(TEMPLATE_PATH):
            with open(TEMPLATE_PATH,"r",encoding="utf-8") as f:
                template = json.load(f)
            try:
                template["context"]["USER_INPUT_BLOCK"]["USER_REQUIREMENTS"] = query
                system_prompt = json.dumps(template["context"],ensure_ascii=False)
            except KeyError:
                system_prompt = ("You are a CVLab AI Scientist.")
        else:
            system_prompt = ("You are a CVLab AI Scientist.")
        # ---------------------------------------------------
        # OpenAI call
        # ----------------------------------------------------
        print(f"[rEasype] Using AI model: {CURRENT_MODEL_KEY} ({MODELS[CURRENT_MODEL_KEY]})")
        response = client.chat.completions.create(
            model=MODELS[CURRENT_MODEL_KEY],
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            #temperature=0.3
        )
        response_text = (response.choices[0].message.content or "")
        print("\n[rEasype] ================= AI RESPONSE =================")
        print(response_text)
        print("[rEasype] =================================================\n")
        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------
        experiment_json = _parse_model_json(response_text)
        if experiment_json is None:
            print("[ERROR] Model did not return valid JSON.")
            experiment_json = _load_dummy_json()
        # ----------------------------------------------------
        # Validate AI-generated experiment
        # ---------------------------------------------------
        validation_errors = _validate_experiment(experiment_json)
        if validation_errors:
            print("[rEasype] AI experiment validation warnings:")
            for error in validation_errors:
                print(f"  - {error}")
        display_response = (_format_experiment_response(experiment_json))
        return jsonify({"ok": True,"response": display_response,"experiment_json": experiment_json,"filename": "rEasype_experiment.json","validation_errors": validation_errors})
    except Exception as e:
        print("\n[rEasype] ================= AI ERROR =================")
        print(f"{type(e).__name__}: {str(e)}")
        traceback.print_exc()
        print("[rEasype] ============================================\n")
        return _return_dummy_response(f"⚠️ OpenAI error: {str(e)}")

# ============================================================
# SAVE
# ============================================================
@ai_bp.route("/save", methods=["POST"])
def save_experiment():
    print("\n[rEasype] >>> SAVE ENDPOINT HIT <<<")
    try:
        data = request.get_json(silent=True)
        print(f"[rEasype] Request JSON type: {type(data)}")
        if data is not None:
            print(json.dumps(data,indent=2,ensure_ascii=False))
        if not isinstance(data, dict):
            return jsonify({"ok": False,"error": "Request body must be a JSON object."}), 400
        experiment = data.get("experiment")
        filename = data.get("filename","rEasype_experiment")
        if experiment is None:
            return jsonify({"ok": False,"error": "No experiment provided."}), 400
        if not isinstance(experiment, dict):
            return jsonify({"ok": False,"error": "experiment must be a JSON object."}), 400
        # --------------------------------------------------------
        # VALIDATE EXPERIMENT
        # --------------------------------------------------------
        validation_errors = _validate_experiment(experiment)
        if validation_errors:
            print("[rEasype] Validation failed:")
            for error in validation_errors:
                print(f"  - {error}")
            return jsonify({"ok": False,"error": "Experiment validation failed.","validation_errors": validation_errors}), 400
        # --------------------------------------------------------
        # CLEAN FILENAME
        # -------------------------------------------------------
        safe_filename = _safe_filename(filename)
        # Make sure the filename has .json
        if not safe_filename.lower().endswith(".json"):
            safe_filename += ".json"
        # --------------------------------------------------------
        # AVOID OVERWRITING EXISTING EXPERIMENTS
        #
        # Example:
        #
        # experiment.json
        # experiment_2.json
        # experiment_3.json
        #
        # The first available filename is selected.
        # --------------------------------------------------------
        base_name = os.path.splitext(safe_filename)[0]
        extension = os.path.splitext(safe_filename)[1]
        candidate = safe_filename
        counter = 2
        while os.path.exists(os.path.join(EXPERIMENTS_PATH,candidate)):
            candidate = (f"{base_name}_{counter}" f"{extension}")
            counter += 1
        safe_filename = candidate
        # --------------------------------------------------------
        # UPDATE EXPERIMENT NAME TO MATCH SAVED FILE
        #
        # This keeps:
        #
        #   metadata.experiment_name
        #
        # consistent with the actual filename.
        # --------------------------------------------------------
        if isinstance(experiment.get("metadata"),dict):
            experiment["metadata"]["experiment_name"] = os.path.splitext(safe_filename)[0]
        # --------------------------------------------------------
        # FINAL PATH
        # --------------------------------------------------------
        experiment_path = os.path.join(EXPERIMENTS_PATH, safe_filename)
        print("[rEasype] Final experiment filename:")
        print(f"  {safe_filename}")
        print("[rEasype] Experiment path:")
        print(f"  {experiment_path}")
        # --------------------------------------------------------
        # SAVE
        # --------------------------------------------------------
        with open(experiment_path,"w",encoding="utf-8") as f:
            json.dump(experiment,f,indent=2,ensure_ascii=False)
        print("[rEasype] SAVE SUCCESS")
        return jsonify({"ok": True,"filename": safe_filename,"path": experiment_path,"message": "Experiment saved successfully."})

    except Exception as e:
        print("\n[rEasype] >>> SAVE EXCEPTION <<<")
        print(f"{type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return jsonify({"ok": False,"error": (f"{type(e).__name__}: " f"{str(e)}")}), 500
# ============================================================
# RUN EXPERIMENT
# ============================================================
@ai_bp.route("/run", methods=["POST"])
def run_experiment():
    print("\n[rEasype] >>> RUN ENDPOINT HIT <<<")
    try:
        data = request.get_json(silent=True) or {}
        experiment = data.get("experiment")
        if experiment is None:
            return jsonify({"ok": False,"error": ("No experiment provided.")}), 400
        validation_errors = (_validate_experiment(experiment))
        if validation_errors:
            return jsonify({"ok": False,"error": ("Experiment validation failed."),"validation_errors":validation_errors}), 400
        experiment_name = (experiment.get("metadata", {}).get("experiment_name","rEasype_experiment"))
        safe_filename = _safe_filename(experiment_name)
        experiment_path = os.path.join(EXPERIMENTS_PATH,safe_filename)
        with open(experiment_path,"w",encoding="utf-8") as f:
            json.dump(experiment,f,indent=2,ensure_ascii=False)
        workflow_script = os.path.join(BASE_PATH,"workflow.py")
        if not os.path.exists(workflow_script):
            print("[rEasype] workflow.py not found.")
            return jsonify({"ok": True,"status": "completed","simulation": True,"message": ("Workflow completed in simulation mode because workflow.py was not found."),"filename": safe_filename})
        result = subprocess.run([sys.executable,workflow_script,experiment_path],capture_output=True,text=True,check=False)
        if result.returncode != 0:
            return jsonify({"ok": False,"status": "failed","error": ("Workflow returned an error."),"return_code":result.returncode,"stdout":result.stdout,"stderr":result.stderr}), 500

        return jsonify({"ok": True,"status": "completed","simulation": False,"filename": safe_filename,"stdout": result.stdout,"stderr": result.stderr})
    except Exception as e:
        print("[rEasype] RUN ERROR")
        traceback.print_exc()
        return jsonify({"ok": False,"status": "failed","error": (f"{type(e).__name__}: {str(e)}")}), 500

# ============================================================
# REPORT
# ============================================================

@ai_bp.route("/report", methods=["POST"])
def get_report():
    print("\n[rEasype] >>> REPORT ENDPOINT HIT <<<")
    try:
        data = request.get_json(silent=True) or {}
        experiment = data.get("experiment")
        if experiment is None:
            return jsonify({"ok": False,"error": ("No experiment provided.")}), 400
        if not isinstance(experiment,dict):
            return jsonify({"ok": False,"error": ("experiment must be " "a JSON object.")}), 400
        metadata = experiment.get("metadata", {})
        experiment_name = metadata.get("experiment_name","Unnamed experiment")
        num_samples = experiment.get("num_samples","N/A")
        report = (
            "rEasype Workflow Report\n"
            "========================\n\n"
            f"Experiment: {experiment_name}\n"
            f"Samples: {num_samples}\n\n"
            "Status: Workflow completed successfully.\n\n"
            "This is currently a placeholder report. "
            "The report endpoint can later be connected "
            "to the experimental data generated by the "
            "robotic platform."
        )
        return jsonify({"ok": True,"report": report})
    except Exception as e:
        print("[rEasype] REPORT ERROR")
        traceback.print_exc()
        return jsonify({"ok": False,"error": (f"{type(e).__name__}: {str(e)}")}), 500

# ============================================================
# MODELS
# ============================================================
@ai_bp.route("/model", methods=["POST"])
def set_model():
    global CURRENT_MODEL_KEY
    try:
        data = request.get_json(silent=True) or {}
        model_key = data.get("model")

        if not model_key:
            return jsonify({
                "ok": False,
                "error": "No model provided."
            }), 400

        if model_key not in MODELS:
            return jsonify({
                "ok": False,
                "error": f"Unknown model '{model_key}'.",
                "available_models": list(MODELS.keys())
            }), 400

        CURRENT_MODEL_KEY = model_key

        print(
            f"[rEasype] AI model changed to: "
            f"{CURRENT_MODEL_KEY} ({MODELS[CURRENT_MODEL_KEY]})"
        )

        return jsonify({
            "ok": True,
            "model": CURRENT_MODEL_KEY,
            "model_name": MODELS[CURRENT_MODEL_KEY],
            "message": "AI model updated successfully."
        })

    except Exception as e:
        print("[rEasype] MODEL SET ERROR")
        traceback.print_exc()

        return jsonify({
            "ok": False,
            "error": f"{type(e).__name__}: {str(e)}"
        }), 500

@ai_bp.route("/models", methods=["GET"])
def get_models():
    return jsonify({
        "ok": True,
        "models": [
            {
                "id": key,
                "name": model,
                "selected": key == CURRENT_MODEL_KEY
            }
            for key, model in MODELS.items()
        ],
        "current_model": CURRENT_MODEL_KEY,
    })
