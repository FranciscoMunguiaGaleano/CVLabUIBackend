from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json


phmeter_bp = Blueprint("/api/v1/phmeter", __name__)

phmeter = devices.ph_meter

@phmeter_bp.route("/read_status", methods=["GET"])
def read_status():
    """Read status of the pH meter."""
    return jsonify(phmeter.read_status)

@phmeter_bp.route("/read_ph", methods=["GET"])
def read_ph():
    """Read pH value, applying calibration."""
    return jsonify(phmeter.read_ph)
        