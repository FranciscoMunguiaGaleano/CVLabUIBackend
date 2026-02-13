from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json
from math import trunc
import re


def truncate_float(number, digits):
    factor = 10 ** digits
    return trunc(number * factor) / factor


echem_bp = Blueprint("/api/v1/echem", __name__)

ROUTINES_DIR = os.getcwd() + "/data/routines/echem"

echem = devices.echem
camera = devices.camera


# ------------------------------------------------------------------
# Camera
# ------------------------------------------------------------------

@echem_bp.route("/capture", methods=["GET"])
def get_image():
    return camera.capture()

# ------------------------------------------------------------------
# Echem arm motion
# ------------------------------------------------------------------
@echem_bp.route("/status", methods=["POST"])
def pipette_arm_status(): 
    msg = echem.status()
    pattern = r"X(?P<X>-?\d+(?:\.\d+)?)Y(?P<Y>-?\d+(?:\.\d+)?)Z(?P<Z>-?\d+(?:\.\d+)?)"
    match = re.search(pattern, msg["response"])
    if match:
        x = truncate_float(float(match.group("X")),3)
        y = truncate_float(float(match.group("Y")),3)
        z = truncate_float(float(match.group("Z")),3)
    return {"message": "[INFO] "+msg["response"], "X":x, "Y":y, "Z":z}
@echem_bp.route("/echem_arm_home", methods=["POST"])
def echem_arm_home(): 
    return echem.home()
@echem_bp.route("/echem_arm_unlock", methods=["GET"])
def echem_arm_unlock(): 
    echem.unlock()
    msg=""
    return msg
@echem_bp.route("/echem_arm_sleep", methods=["GET"])
def echem_arm_sleep(): 
    echem.sleep()
    msg=""
    return msg
@echem_bp.route("/echem_arm_reset", methods=["GET"])
def echem_arm_reset(): 
    echem.reset()
    msg=""
    return msg
@echem_bp.route("/echem_arm_send_gcode", methods=["POST"])
def echem_arm_send_gcode():
    data=request.json
    gcode = data["gcode"] 
    msg = echem.send_gcode(gcode)['response']
    return jsonify({"message": msg})
@echem_bp.route("/echem_arm_execute_routine", methods=["POST"])
def echem_arm_execute_routine():# POST
    data=request.json
    file = data["file"] 
    echem.execute_routine(file)
    msg=""
    return msg
# ------------------------------------------------------------------
# Echem polisher, dropper and camera
# ------------------------------------------------------------------
# ------------------------------------------------------------------
# Polisher control
# ------------------------------------------------------------------
@echem_bp.route("/echem_polisher_on", methods=["POST"])
def polisher_on():
    msg = {"message":"[INFO] Polisher ON"}
    echem.polisher_on()
    return jsonify(msg)
@echem_bp.route("/echem_polisher_off", methods=["POST"])
def polisher_off():
    msg = {"message": "[INFO] Polisher OFF"}
    echem.polisher_off()
    return jsonify(msg)
# ------------------------------------------------------------------
# Alumina dropper
# ------------------------------------------------------------------
@echem_bp.route("/echem_polisher_dropper_on", methods=["POST"])
def polisher_dropper_on():
    msg = {"message":"[INFO] Dropper ON"}
    echem.polisher_dropper_on()
    return jsonify(msg)

@echem_bp.route("/echem_polisher_dropper_off", methods=["POST"])
def polisher_dropper_off():
    msg = {"message": "[INFO] Dropper OFF"}
    echem.polisher_dropper_off
    return jsonify(msg)
# ------------------------------------------------------------------
# Electrodes vertical translation
# ------------------------------------------------------------------
@echem_bp.route("/echem_raise_electrodes", methods=["POST"])
def raise_electrodes():
    msg = {"message":"[INFO] Raising electrodes"}
    echem.raise_electrodes()
    return jsonify(msg)
@echem_bp.route("/echem_lower_electrodes", methods=["POST"])
def lower_electrodes():
    msg = {"message": "[INFO] Lowering electrodes"}
    echem.lower_electrodes()
    return jsonify(msg)
# ------------------------------------------------------------------
# Pipette endpoint to load and save changes in routines files
# ------------------------------------------------------------------
@echem_bp.route("/routines", methods=["GET"])
def list_routines():
    try:
        files = [
            f for f in os.listdir(ROUTINES_DIR)
            if f.endswith(".json")
        ]
        return jsonify({"routines": sorted(files)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@echem_bp.route("/routines/load/<string:name>", methods=["GET"])
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

@echem_bp.route("/routines/save/<string:name>", methods=["POST"])
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
@echem_bp.route("/jog_x", methods=["POST"])
def jog_x():
    data = request.json or {}
    step = truncate_float(float(data.get("step")),3)
    status = echem.status()["response"]
    X_axis = float(status.split("X")[1].split("Y")[0])
    Y_axis = float(status.split("Y")[1].split("Z")[0])
    Z_axis = float(status.split("Z")[1].split("GRIPPER")[0])
    X_delta = X_axis+step
    if X_delta<0:
        X_delta = X_axis
    gcode=f"G1 X{X_delta} Y{Y_axis} Z{Z_axis} F100"
    echem.send_gcode(gcode)
    echem.X_axis = X_delta
    return jsonify({"message": f"[INFO] Jogging x axis: {gcode}"})


@echem_bp.route("/jog_y", methods=["POST"])
def jog_y():
    data = request.json or {}
    step = truncate_float(float(data.get("step")),3)
    status = echem.status()["response"]
    pattern = r"X(?P<X>-?\d+(?:\.\d+)?)Y(?P<Y>-?\d+(?:\.\d+)?)Z(?P<Z>-?\d+(?:\.\d+)?)"
    match = re.search(pattern, status)
    if match:
        X_axis = float(match.group("X"))
        Y_axis = float(match.group("Y"))
        Z_axis = float(match.group("Z"))
        print(Y_axis)
        Y_delta = Y_axis+step
        if Y_delta<0:
            Y_delta = Y_axis
        gcode=f"G1 X{X_axis} Y{Y_delta} Z{Z_axis}"
        print(gcode, step)
        echem.send_gcode(gcode)
        echem.Y_axis = Y_delta
        return jsonify({"message": f"[INFO] Jogging y axis: {gcode}"})
    else:
        return jsonify({"message": f"[ERROR] The controller in unavailable."})


@echem_bp.route("/jog_z", methods=["POST"])
def jog_z():
    data = request.json or {}
    step = truncate_float(float(data.get("step")),3)
    status = echem.status()["response"]
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
        echem.send_gcode(gcode)
        echem.Z_axis = Z_delta
        return jsonify({"message": f"[INFO] Jogging y axis: {gcode}"})
    else:
        return jsonify({"message": f"[ERROR] The controller in unavailable."})
    
