from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json
import time

from math import trunc

def truncate_float(number, digits):
    factor = 10 ** digits
    return trunc(number * factor) / factor

robot_bp = Blueprint("/api/v1/robot", __name__)

ROUTINES_DIR = os.getcwd() + "/data/routines/arm"

arm = devices.arm



@robot_bp.route("/arm/status", methods=["POST"])
def arm_status():
    try:
        status=arm.status()["response"]
        print(status)
        X = truncate_float(float(status.split("X")[1].split("Y")[0]),3)
        print(f"X{X}")
        Y = truncate_float(float(status.split("Y")[1].split("Z")[0]),3)
        print(f"X{Y}")
        Z = truncate_float(float(status.split("Z")[1].split("GRIPPER")[0]),3)
        print(f"X{Z}")
        GRIPPER = 0
        print("aki")
        print({"message": f"[INFO] State: X {X} Y {Y} Z {Z} GRIPPER {GRIPPER}",
                        "X": X,
                        "Y": Y,
                        "Z": Z,
                        "GRIPPER": GRIPPER})
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
    arm.X_axis = 0.0
    arm.Y_axis = 0.0
    arm.Z_axis = 0.0
    return jsonify({"message": "[INFO] Homing arm."})


@robot_bp.route("/arm/open_gripper", methods=["POST"])
def open_gripper():
    arm.open_gripper()
    return jsonify({"message": "[INFO] Gripper open"})


@robot_bp.route("/arm/close_gripper", methods=["POST"])
def close_gripper():
    arm.close_gripper()
    return jsonify({"message": "[INFO] Gripper closed"})

@robot_bp.route("/arm/gcode", methods=["POST"])
def send_gcode():
    data = request.json
    print(data)
    gcode = data.get("gcode")
    if not gcode:
        return jsonify({"error": "Missing gcode"}), 400

    response = arm.send_gcode(gcode)
    print(response)
    return jsonify({"ok": True, "gcode": gcode})

@robot_bp.route("/arm/jog_x", methods=["POST"])
def jog_x():
    data = request.json or {}
    step = truncate_float(float(data.get("step")),3)
    status = arm.status()["response"]
    X_axis = float(status.split("X")[1].split("Y")[0])
    Y_axis = float(status.split("Y")[1].split("Z")[0])
    Z_axis = float(status.split("Z")[1].split("GRIPPER")[0])
    X_delta = X_axis+step
    if X_delta<0:
        X_delta = X_axis
    gcode=f"G1 X{X_delta} Y{Y_axis} Z{Z_axis} F100"
    arm.send_gcode(gcode)
    arm.X_axis = X_delta
    return jsonify({"message": f"[INFO] Jogging x axis: {gcode}"})


@robot_bp.route("/arm/jog_y", methods=["POST"])
def jog_y():
    data = request.json or {}
    step = truncate_float(float(data.get("step")),3)
    status = arm.status()["response"]
    X_axis = float(status.split("X")[1].split("Y")[0])
    Y_axis = float(status.split("Y")[1].split("Z")[0])
    Z_axis = float(status.split("Z")[1].split("GRIPPER")[0])
    Y_delta = Y_axis+step
    if Y_delta<0:
        Y_delta = Y_axis
    gcode=f"G1 X{X_axis} Y{Y_delta} Z{Z_axis}"
    arm.send_gcode(gcode)
    arm.Y_axis = Y_delta
    return jsonify({"message": f"[INFO] Jogging y axis: {gcode}"})


@robot_bp.route("/arm/jog_z", methods=["POST"])
def jog_z():
    data = request.json or {}
    step = truncate_float(float(data.get("step")),3)
    status = arm.status()["response"]
    X_axis = float(status.split("X")[1].split("Y")[0])
    Y_axis = float(status.split("Y")[1].split("Z")[0])
    Z_axis = float(status.split("Z")[1].split("GRIPPER")[0])
    Z_delta = Z_axis+step
    if Z_delta<0:
        Z_delta = Z_axis
    gcode=f"G1 X{X_axis} Y{Y_axis} Z{Z_delta}"
    arm.send_gcode(gcode)
    arm.Z_axis = Z_delta
    return jsonify({"message": f"[INFO] Jogging z axis: {gcode}"})

