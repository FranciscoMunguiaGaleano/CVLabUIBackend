from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json


capper_bp = Blueprint("/api/v1/capper", __name__)

capper = devices.capper

@capper_bp.route("/home", methods=["GET"])
def home():
    """Move capper to home position."""
    capper.home()
    return jsonify({"message":'[INFO] Moving capper to home position.'})
@capper_bp.route("/hold_vial", methods=["GET"])
def hold_vial():
    """Hold vial in position."""
    capper.hold_vial()
    return jsonify({"message":'[INFO] Holding vial...'})
@capper_bp.route("/release_vial", methods=["GET"])
def release_vial():
    """Release vial from capper."""
    capper.release_vial()
    return jsonify({"message":'[INFO] Releasing vial...'})
@capper_bp.route("/uncap", methods=["GET"])
def uncap():
    """Remove the cap from the vial."""
    capper.uncap()
    return jsonify({"message":'[INFO] Uncapping...'})
@capper_bp.route("/cap", methods=["GET"])
def cap():
    """Place the cap onto the vial."""
    capper.cap()
    return jsonify({"message":'[INFO] Capping...'})
