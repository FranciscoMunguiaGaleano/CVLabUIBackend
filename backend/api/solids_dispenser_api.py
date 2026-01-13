from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json


quantos_bp = Blueprint("/api/v1/quantos", __name__)

solids_dispenser = devices.solids_dispenser

# ------------------------------------------------------------------
# Status
# ------------------------------------------------------------------
@quantos_bp.route("/status", methods=["GET"])
def arm_status():
    return jsonify(solids_dispenser.status())
# ------------------------------------------------------------------
# Sample data and balance
# ------------------------------------------------------------------
@quantos_bp.route("/get_sample_data", methods=["GET"])
def get_sample_data():
    return jsonify(solids_dispenser.get_sample_data())

@quantos_bp.route("/tare_balance", methods=["GET"])
def tare_balance():
    return jsonify(solids_dispenser.tare_balance())
@quantos_bp.route("/dispense", methods=["POST"])
def dispense():
    data = request.json
    return jsonify(solids_dispenser.dispense(data))
@quantos_bp.route("/set_target_mass", methods=["POST"])
def set_target_mass():
    data = request.json
    mass = data.get("mass")
    #print(f"Homlis {mass}")
    try:
        if not mass or float(mass) > 200 or float(mass) <=0:
            return jsonify({"error": "Not valid mass"})
    except:
        return jsonify({"error": "Mass value must be a number"})

    return jsonify(solids_dispenser.set_target_mass(data))
# ------------------------------------------------------------------
# Dosing head control
# ------------------------------------------------------------------
@quantos_bp.route("/lock_dosing_head", methods=["GET"])
def lock_dosing_head():
    return jsonify(solids_dispenser.lock_dosing_head())
@quantos_bp.route("/unlock_dosing_head", methods=["GET"])
def unlock_dosing_head():
    return jsonify(solids_dispenser.unlock_dosing_head())
# ------------------------------------------------------------------
# Door control
# ------------------------------------------------------------------
@quantos_bp.route("/open_front_door", methods=["GET"])
def open_front_door():
    return jsonify(solids_dispenser.open_front_door())
@quantos_bp.route("/close_front_door", methods=["GET"])
def close_front_door():
    return jsonify(solids_dispenser.close_front_door())
@quantos_bp.route("/open_side_door", methods=["GET"])
def open_side_doors():
    return jsonify(solids_dispenser.open_side_doors())
@quantos_bp.route("/close_side_door", methods=["GET"])
def close_side_doors():
    return jsonify(solids_dispenser.close_side_doors())