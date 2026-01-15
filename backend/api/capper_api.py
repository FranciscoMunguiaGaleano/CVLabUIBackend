from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json


capper_bp = Blueprint("/api/v1/capper", __name__)

capper = devices.capper

@capper_bp.route("/home", methods=["GET"])
def home():
    """Move capper to home position."""
    return jsonify(capper.home())
@capper_bp.route("/hold_vial", methods=["GET"])
def hold_vial():
    """Hold vial in position."""
    return jsonify(capper.hold_vial())
@capper_bp.route("/release_vial", methods=["GET"])
def release_vial():
    """Release vial from capper."""
    return jsonify(capper.release_vial())
@capper_bp.route("/uncap", methods=["GET"])
def uncap():
    """Remove the cap from the vial."""
    return jsonify(capper.uncap())
@capper_bp.route("/cap", methods=["GET"])
def cap():
    """Place the cap onto the vial."""
    return jsonify(capper.cap())
