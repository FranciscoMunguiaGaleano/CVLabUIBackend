from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json



robot_bp = Blueprint("/api/v1/robot", __name__)

ROUTINES_DIR = os.getcwd() + "/data/routines/arm"

arm = devices.arm




@robot_bp.route("/arm/status", methods=["GET"])
def arm_status():
    return jsonify(arm.status())

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
    return jsonify({"ok": True})


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
    step = data.get("step")
    # TODO: arm.jog_x(step)
    return jsonify({"ok": True})


@robot_bp.route("/arm/jog_y", methods=["POST"])
def jog_y():
    data = request.json or {}
    step = data.get("step")
    # TODO: arm.jog_y(step)
    return jsonify({"ok": True})


@robot_bp.route("/arm/jog_z", methods=["POST"])
def jog_z():
    data = request.json or {}
    step = data.get("step")
    # TODO: arm.jog_z(step)
    return jsonify({"ok": True})

