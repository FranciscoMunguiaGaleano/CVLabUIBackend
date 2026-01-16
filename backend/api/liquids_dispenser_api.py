from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json


liquids_dispenser_bp = Blueprint("/api/v1/liquids_dispenser", __name__)

liquids_dispenser = devices.liquids_dispenser

# ------------------------------------------------------------------
# Piston control
# ------------------------------------------------------------------
@liquids_dispenser_bp.route("/piston_to_dispense_position", methods=["GET"])
def piston_to_dispense_position():
    msg={"message":"[INFO] Moving piston to dispensing position."}
    liquids_dispenser.piston_to_dispense_position()
    return jsonify(msg)
@liquids_dispenser_bp.route("/piston_to_home_position", methods=["GET"])
def piston_to_home_position():
    msg={"message":"[INFO] Return piston to home position."}
    liquids_dispenser.piston_to_home_position()
    return jsonify(msg)

# ------------------------------------------------------------------
# Status and valve
# ------------------------------------------------------------------
@liquids_dispenser_bp.route("/status", methods=["GET"])
def status():
    """Reading status"""
    msg = liquids_dispenser.status()
    return jsonify(msg)
@liquids_dispenser_bp.route("/get_valve_pos", methods=["GET"])
def get_valve_pos():
    """Getting valve position"""
    msg = liquids_dispenser.get_valve_pos()
    return jsonify(msg)

# ------------------------------------------------------------------
# Dispensing
# ------------------------------------------------------------------
@liquids_dispenser_bp.route("/dispense", methods=["POST"])
def dispense():
    data = request.json or {}
    msg=liquids_dispenser.dispense(data)
    return jsonify(msg)
@liquids_dispenser_bp.route("/move_home", methods=["GET"])
def move_home():
    """Move the syringe pump to home position."""
    msg=liquids_dispenser.move_home()
    return jsonify(msg)
@liquids_dispenser_bp.route("/set_waste_port", methods=["POST"])
def set_waste_port():
    """Set the waste port."""
    data = request.json or {}
    msg=liquids_dispenser.set_waste_port(data)
    return jsonify(msg)