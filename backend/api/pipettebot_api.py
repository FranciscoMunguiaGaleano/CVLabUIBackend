from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json
from math import trunc
import re






def truncate_float(number, digits):
    factor = 10 ** digits
    return trunc(number * factor) / factor


pipettebot_bp = Blueprint("/api/v1/pipettebot", __name__)

ROUTINES_DIR = os.getcwd() + "/data/routines/pipette"

pipettebot = devices.echem

# ------------------------------------------------------------------
# Pipette arm motion
# ------------------------------------------------------------------
@pipettebot_bp.route("/status", methods=["POST"])
def pipette_arm_status(): 
    msg=pipettebot.pipette_arm_status()
    pattern = r"X(?P<X>-?\d+(?:\.\d+)?)Y(?P<Y>-?\d+(?:\.\d+)?)Z(?P<Z>-?\d+(?:\.\d+)?)"
    match = re.search(pattern, msg["response"])
    if match:
        x = float(match.group("X"))
        y = float(match.group("Y"))
        z = float(match.group("Z"))
    return {"message": "[INFO] "+msg["response"], "X":x, "Y":y, "Z":z}
@pipettebot_bp.route("/pipette_arm_home", methods=["POST"])
def pipette_arm_home(): 
    return pipettebot.pipette_arm_home()
@pipettebot_bp.route("/pipette_arm_unlock", methods=["GET"])
def pipette_arm_unlock(): 
    pipettebot.pipette_arm_unlock()
    msg=""
    return msg
@pipettebot_bp.route("/pipette_arm_sleep", methods=["GET"])
def pipette_arm_sleep(): 
    pipettebot.pipette_arm_sleep()
    msg=""
    return msg
@pipettebot_bp.route("/pipette_arm_reset", methods=["GET"])
def pipette_arm_reset(): 
    pipettebot.pipette_arm_reset()
    msg=""
    return msg
@pipettebot_bp.route("/pipette_arm_send_gcode", methods=["POST"])
def pipette_arm_send_gcode():
    data=request.json
    gcode = data["gcode"] 
    msg = pipettebot.pipette_arm_send_gcode(gcode)['response']
    return jsonify({"message": msg})
@pipettebot_bp.route("/pipette_arm_execute_routine", methods=["POST"])
def pipette_arm_execute_routine():# POST
    data=request.json
    file = data["file"] 
    pipettebot.pipette_arm_execute_routine(file)
    msg=""
    return msg
# ------------------------------------------------------------------
# Pipette servo/head
# ------------------------------------------------------------------
@pipettebot_bp.route("/pipette_home", methods=["POST"])
def pipette_home(): 
    msg = pipettebot.pipette_home()
    return jsonify({"message":"[INFO] Homing pipette."})
@pipettebot_bp.route("/pipette_eject_tip", methods=["POST"])
def pipette_eject_tip(): 
    msg=pipettebot.pipette_eject_tip()
    return jsonify({"message":"[INFO] Ejecting Tip"})
@pipettebot_bp.route("/pipette_preload", methods=["POST"])
def pipette_preload(): 
    msg=pipettebot.pipette_preload()
    return jsonify({"message":"[INFO] Preloading pipette."})
@pipettebot_bp.route("/pipette_load", methods=["POST"])
def pipette_load(): 
    msg=pipettebot.pipette_load()
    return jsonify({"message":"[INFO] Loading pipette"})
@pipettebot_bp.route("/pipette_unload", methods=["POST"])
def pipette_unload(): 
    msg=pipettebot.pipette_unload()
    return jsonify({"message":"[INFO] Sampling..."})
@pipettebot_bp.route("/pipette_set_speed", methods=["POST"])
def pipette_set_speed(speed): 
    data=request.json
    speed = data["speed"] 
    pipettebot.pipette_set_speed(speed)
    msg=""
    return msg
# ------------------------------------------------------------------
# Pipette endpoint to load and save changes in routines files
# ------------------------------------------------------------------
@pipettebot_bp.route("/routines", methods=["GET"])
def list_routines():
    try:
        files = [
            f for f in os.listdir(ROUTINES_DIR)
            if f.endswith(".json")
        ]
        return jsonify({"routines": sorted(files)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@pipettebot_bp.route("/routines/load/<string:name>", methods=["GET"])
def load_routine(name):
    path = os.path.join(ROUTINES_DIR, name)

    if not os.path.isfile(path):
        return jsonify({"error": "Routine not found"}), 404

    try:
        with open(path, "r") as f:
            data = json.load(f)

        gcodes = data.get("GCODES", [])
        #g1_only = [g for g in gcodes if g.strip().startswith("G1")]

        return jsonify({
            "message": f"[INFO] Routine {name} has been loaded.",
            "name": name,
            "gcodes": gcodes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@pipettebot_bp.route("/routines/save/<string:name>", methods=["POST"])
def save_routine(name):
    """
    Save updated GCODES from the frontend table into the routine file.
    Expects JSON payload like:
    {
        "gcodes": ["G90", "G21", "G1 X10", "M100", "M200"]
    }
    """
    path = os.path.join(ROUTINES_DIR, name)

    if not os.path.isfile(path):
        return jsonify({"error": "Routine not found"}), 404

    try:
        # Get the updated gcodes from request body
        data = request.get_json()
        if not data or "gcodes" not in data:
            return jsonify({"error": "Missing 'gcodes' in request"}), 400

        updated_gcodes = data["gcodes"]

        # Save the updated GCODES to the file
        with open(path, "w") as f:
            json.dump({"GCODES": updated_gcodes}, f, indent=4)

        return jsonify({
            "message": f"[INFO] Routine {name} has been updated successfully.",
            "name": name,
            "gcodes": updated_gcodes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------------------------------------------------------
# Jogging routines
# ------------------------------------------------------------------
@pipettebot_bp.route("/jog_x", methods=["POST"])
def jog_x():
    data = request.json or {}
    step = truncate_float(float(data.get("step")),3)
    status = pipettebot.pipette_arm_status()["response"]
    X_axis = float(status.split("X")[1].split("Y")[0])
    Y_axis = float(status.split("Y")[1].split("Z")[0])
    Z_axis = float(status.split("Z")[1].split("GRIPPER")[0])
    X_delta = X_axis+step
    if X_delta<0:
        X_delta = X_axis
    gcode=f"G1 X{X_delta} Y{Y_axis} Z{Z_axis} F100"
    pipettebot.pipette_arm_send_gcode(gcode)
    pipettebot.pipette_arm_set_X_axis(X_delta)
    return jsonify({"message": f"[INFO] Jogging x axis: {gcode}"})


@pipettebot_bp.route("/jog_z", methods=["POST"])
def jog_z():
    data = request.json or {}
    step = truncate_float(float(data.get("step")),3)
    status = pipettebot.pipette_arm_status()["response"]
    pattern = r"X(?P<X>-?\d+(?:\.\d+)?)Y(?P<Y>-?\d+(?:\.\d+)?)Z(?P<Z>-?\d+(?:\.\d+)?)"
    match = re.search(pattern, status)
    if match:
        X_axis = float(match.group("X"))
        Y_axis = float(match.group("Y"))
        Z_axis = float(match.group("Z"))
        print(Z_axis)
        Z_delta = Z_axis+step
        if Z_delta<0:
            Z_delta = Z_axis
        gcode=f"G1 X{X_axis} Y{Y_axis} Z{Z_delta}"
        print(gcode, step)
        pipettebot.pipette_arm_send_gcode(gcode)
        pipettebot.pipette_arm_set_Z_axis(Z_delta)
        return jsonify({"message": f"[INFO] Jogging y axis: {gcode}"})
    else:
        return jsonify({"message": f"[ERROR] The controller in unavailable."})