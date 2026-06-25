from flask import Blueprint, jsonify, request
from devices.device_manager import devices

import os
import json
import re

from math import trunc


# ---------------------------------------------------
# Utils
# ---------------------------------------------------

def truncate_float(number, digits):
    factor = 10 ** digits
    return trunc(number * factor) / factor


robot_bp = Blueprint("/api/v1/robot", __name__)

ROUTINES_DIR = os.getcwd() + "/data/routines/arm"

arm = devices.arm


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def get_current_position():
    """
    Reads current XYZ position from robot status.
    """

    status = arm.status()["response"]

    X = truncate_float(float(status.split("X")[1].split("Y")[0]), 3)
    Y = truncate_float(float(status.split("Y")[1].split("Z")[0]), 3)
    Z = truncate_float(float(status.split("Z")[1].split("GRIPPER")[0]), 3)

    return X, Y, Z


def extract_axis(gcode, axis):
    """
    Extract axis from GCODE.

    Example:
        extract_axis("G1 X10 Y20", "X")
    """

    match = re.search(rf"{axis}(-?\d+\.?\d*)", gcode)

    if match:
        return float(match.group(1))

    return None


def ensure_feedrate(gcode, default_feedrate=500):
    """
    Automatically add feedrate if missing.
    """

    if gcode.startswith("G1") and "F" not in gcode:
        gcode += f" F{default_feedrate}"

    return gcode


def update_cached_position(gcode):
    """
    Updates cached arm coordinates from G1 commands.
    """

    if not gcode.startswith("G1"):
        return

    x = extract_axis(gcode, "X")
    y = extract_axis(gcode, "Y")
    z = extract_axis(gcode, "Z")

    if x is not None:
        arm.X_axis = truncate_float(x, 3)

    if y is not None:
        arm.Y_axis = truncate_float(y, 3)

    if z is not None:
        arm.Z_axis = truncate_float(z, 3)


def process_special_commands(gcode):
    """
    Handles custom M commands.
    """

    command = gcode.strip()

    if command == "M100":
        arm.open_gripper()

        return {
            "ok": True,
            "message": "[INFO] Gripper open"
        }

    elif command == "M200":
        arm.close_gripper()

        return {
            "ok": True,
            "message": "[INFO] Gripper closed"
        }

    return None


def send_robot_gcode(gcode):
    """
    Centralized GCODE handler.

    Features:
    - Handles M100/M200
    - Injects feedrate automatically
    - Updates cached XYZ
    """

    # Handle custom commands first
    special = process_special_commands(gcode)

    if special:
        return special

    # Ensure feedrate exists
    gcode = ensure_feedrate(gcode)

    # Send to robot
    response = arm.send_gcode(gcode)

    print(response)

    # Update cached XYZ
    update_cached_position(gcode)

    return {
        "ok": True,
        "gcode": gcode
    }


def jog_axis(axis, step):
    """
    Generic jog helper.
    """

    X, Y, Z = get_current_position()

    if axis == "X":
        X = max(0, truncate_float(X + step, 3))

    elif axis == "Y":
        Y = max(0, truncate_float(Y + step, 3))

    elif axis == "Z":
        Z = max(0, truncate_float(Z + step, 3))

    gcode = f"G1 X{X} Y{Y} Z{Z}"

    send_robot_gcode(gcode)

    return gcode


# ---------------------------------------------------
# Status
# ---------------------------------------------------

@robot_bp.route("/arm/status", methods=["POST"])
def arm_status():

    try:

        X, Y, Z = get_current_position()

        GRIPPER = 0

        return jsonify({
            "message": f"[INFO] State: X {X} Y {Y} Z {Z} GRIPPER {GRIPPER}",
            "X": X,
            "Y": Y,
            "Z": Z,
            "GRIPPER": GRIPPER
        })

    except Exception as e:

        return jsonify({
            "message": f"[ERROR] {e}"
        })


# ---------------------------------------------------
# Routines
# ---------------------------------------------------

@robot_bp.route("/arm/routines", methods=["GET"])
def list_arm_routines():

    try:

        files = [
            f for f in os.listdir(ROUTINES_DIR)
            if f.endswith(".json")
        ]

        return jsonify({
            "routines": sorted(files)
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@robot_bp.route("/arm/routines/load/<string:name>", methods=["GET"])
def load_arm_routine(name):

    path = os.path.join(ROUTINES_DIR, name)

    if not os.path.isfile(path):

        return jsonify({
            "error": "Routine not found"
        }), 404

    try:

        with open(path, "r") as f:
            data = json.load(f)

        gcodes = data.get("GCODES", [])

        return jsonify({
            "message": f"[INFO] Routine {name} has been loaded.",
            "name": name,
            "gcodes": gcodes
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@robot_bp.route("/arm/routines/save/<string:name>", methods=["POST"])
def save_arm_routine(name):

    path = os.path.join(ROUTINES_DIR, name)

    if not os.path.isfile(path):

        return jsonify({
            "error": "Routine not found"
        }), 404

    try:

        data = request.get_json()

        if not data or "gcodes" not in data:

            return jsonify({
                "error": "Missing 'gcodes' in request"
            }), 400

        updated_gcodes = data["gcodes"]

        with open(path, "w") as f:

            json.dump({
                "GCODES": updated_gcodes
            }, f, indent=4)

        return jsonify({
            "message": f"[INFO] Routine {name} updated successfully.",
            "name": name,
            "gcodes": updated_gcodes
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ---------------------------------------------------
# Robot Controls
# ---------------------------------------------------

@robot_bp.route("/arm/home", methods=["POST"])
def arm_home():

    arm.home()

    arm.X_axis = 0.0
    arm.Y_axis = 0.0
    arm.Z_axis = 0.0

    return jsonify({
        "message": "[INFO] Homing arm."
    })


@robot_bp.route("/arm/open_gripper", methods=["POST"])
def open_gripper():

    arm.open_gripper()

    return jsonify({
        "message": "[INFO] Gripper open"
    })


@robot_bp.route("/arm/close_gripper", methods=["POST"])
def close_gripper():

    arm.close_gripper()

    return jsonify({
        "message": "[INFO] Gripper closed"
    })


# ---------------------------------------------------
# GCODE
# ---------------------------------------------------

@robot_bp.route("/arm/gcode", methods=["POST"])
def send_gcode():

    data = request.json or {}

    print(data)

    gcode = data.get("gcode")

    if not gcode:

        return jsonify({
            "error": "Missing gcode"
        }), 400

    result = send_robot_gcode(gcode)

    return jsonify(result)


# ---------------------------------------------------
# Jogging
# ---------------------------------------------------

@robot_bp.route("/arm/jog_x", methods=["POST"])
def jog_x():

    data = request.json or {}

    step = truncate_float(float(data.get("step")), 3)

    gcode = jog_axis("X", step)

    return jsonify({
        "message": f"[INFO] Jogging x axis: {gcode}"
    })


@robot_bp.route("/arm/jog_y", methods=["POST"])
def jog_y():

    data = request.json or {}

    step = truncate_float(float(data.get("step")), 3)

    gcode = jog_axis("Y", step)

    return jsonify({
        "message": f"[INFO] Jogging y axis: {gcode}"
    })


@robot_bp.route("/arm/jog_z", methods=["POST"])
def jog_z():

    data = request.json or {}

    step = truncate_float(float(data.get("step")), 3)

    gcode = jog_axis("Z", step)

    return jsonify({
        "message": f"[INFO] Jogging z axis: {gcode}"
    })
