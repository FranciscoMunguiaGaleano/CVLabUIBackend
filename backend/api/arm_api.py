from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json
import time



robot_bp = Blueprint("/api/v1/robot", __name__)

ROUTINES_DIR = os.getcwd() + "/data/routines/arm"

arm = devices.arm



@robot_bp.route("/arm/status", methods=["POST"])
def arm_status():
    try:
        status=arm.status()["response"]
        X = float(status.split("X")[1].split("Y")[0])
        Y = float(status.split("Y")[1].split("Z")[0])
        Z = float(status.split("Z")[1].split("GRIPPER")[0])
        GRIPPER = int(status.split("GRIPPER")[1])
        return jsonify({"message": f"[INFO] State: X {X} Y {Y} Z {Z} GRIPPER {GRIPPER}",
                        "X": X,
                        "Y": Y,
                        "Z": Z,
                        "GRIPPER": GRIPPER})
    except Exception as e:
        return jsonify({"message": f"[ERROR] {e}"})
    

@robot_bp.route("/arm/routines", methods=["GET"])
def list_arm_routines():
    try:
        files = [
            f for f in os.listdir(ROUTINES_DIR)
            if f.endswith(".json")
        ]
        return jsonify({"routines": sorted(files)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@robot_bp.route("/arm/routines/<string:name>", methods=["GET"])
def load_arm_routine(name):
    path = os.path.join(ROUTINES_DIR, name)

    if not os.path.isfile(path):
        return jsonify({"error": "Routine not found"}), 404

    try:
        with open(path, "r") as f:
            data = json.load(f)

        gcodes = data.get("GCODES", [])
        g1_only = [g for g in gcodes if g.strip().startswith("G1")]

        return jsonify({
            "name": name,
            "gcodes": g1_only
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@robot_bp.route("/arm/home", methods=["POST"])
def arm_home():
    arm.home()
    return jsonify({"message": "[INFO] Homing arm."})


@robot_bp.route("/arm/open_gripper", methods=["POST"])
def open_gripper():
    arm.open_gripper()
    return jsonify({"ok": True})


@robot_bp.route("/arm/close_gripper", methods=["POST"])
def close_gripper():
    arm.close_gripper()
    return jsonify({"ok": True})

@robot_bp.route("/arm/gcode", methods=["POST"])
def send_gcode():
    data = request.json
    gcode = data.get("gcode")
    if not gcode:
        return jsonify({"error": "Missing gcode"}), 400

    arm.send_gcode(gcode)
    return jsonify({"ok": True, "gcode": gcode})

@robot_bp.route("/arm/jog_x", methods=["POST"])
def jog_x():
    data = request.json or {}
    step = float(data.get("step"))
    status = arm.status()["response"]
    X_axis = float(status.split("X")[1].split("Y")[0])
    Y_axis = float(status.split("Y")[1].split("Z")[0])
    Z_axis = float(status.split("Z")[1].split("GRIPPER")[0])
    X_delta = X_axis+step
    gcode=f"G1 X{X_delta} Y{Y_axis} Z{Z_axis}"
    arm.send_gcode(gcode)
    return jsonify({"message": f"[INFO] Jogging z axis: {gcode}"})


@robot_bp.route("/arm/jog_y", methods=["POST"])
def jog_y():
    data = request.json or {}
    step = float(data.get("step"))
    positions = arm.status()["response"]
    X_axis = float(positions["X"])
    Y_axis=float(positions["Y"])
    Z_axis=float(positions["Z"])
    Y_delta = Y_axis+step
    gcode=f"G1 X{X_axis} Y{Y_delta} Z{Z_axis}"
    arm.send_gcode(gcode)
    return jsonify({"message": f"[INFO] Jogging z axis: {gcode}"})


@robot_bp.route("/arm/jog_z", methods=["POST"])
def jog_z():
    data = request.json or {}
    step = float(data.get("step"))
    positions = arm.status()["response"]
    X_axis = float(positions["X"])
    Y_axis=float(positions["Y"])
    Z_axis=float(positions["Z"])
    Z_delta = Z_axis+step
    gcode=f"G1 X{X_axis} Y{Y_axis} Z{Z_delta}"
    arm.send_gcode(gcode)
    return jsonify({"message": f"[INFO] Jogging z axis: {gcode}"})

