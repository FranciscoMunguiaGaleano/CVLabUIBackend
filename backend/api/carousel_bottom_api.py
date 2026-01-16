from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json


bottom_carousel_bp = Blueprint("/api/v1/bottom_carousel", __name__)

bottom_carousel = devices.bottom_carousel

@bottom_carousel_bp.route("/home", methods=["GET"])
def home():
    """Home the carousel."""
    msg = {"message":"[INFO] Homing Bottom Carousel..."}
    bottom_carousel.home()
    return jsonify(msg)

@bottom_carousel_bp.route("/move_absolute", methods=["POST"])
def move_absolute():
    """Move carousel to an absolute position."""
    data = request.json or {}
    pos = data.get("pos")
    position = bottom_carousel.positions[str(pos)]
    print(position)
    msg = {"message": f"[INFO] Moving Bottom Carousel absolute position {pos} at {position} degrees"}
    bottom_carousel.move_absolute(str(pos))
    return jsonify(msg)

@bottom_carousel_bp.route("/move_incremental", methods=["POST"])
def move_incremental():
    """Move carousel by a step increment."""
    data = request.json or {}
    step = data.get("step")
    bottom_carousel.step = float(step)
    msg = {"message":f"[INFO] Moving Bottom Carousel incrementally to {bottom_carousel.position:.2f} degrees"}
    bottom_carousel.move_incremental()
    return jsonify(msg)

# Pumps control
@bottom_carousel_bp.route("/turn_pumps_on", methods=["GET"])
def turn_pumps_on():
    msg = {"message":"[INFO] Turning pumps on."}
    bottom_carousel.turn_pumps_on()
    return jsonify(msg)

@bottom_carousel_bp.route("/turn_pumps_off", methods=["GET"])
def turn_pumps_off():
    msg = {"message":"[INFO] Turning pumps off."}
    bottom_carousel.turn_pumps_off()
    return jsonify(msg)
    
# Purger control
@bottom_carousel_bp.route("/turn_purger_on", methods=["GET"])
def turn_purger_on():
    msg = {"message":"[INFO] Turning purger on."}
    bottom_carousel.turn_purger_on()
    return jsonify(msg)

@bottom_carousel_bp.route("/turn_purger_off", methods=["GET"])
def turn_purger_off():
    msg = {"message":"[INFO] Turning purger off."}
    bottom_carousel.turn_purger_off()
    return jsonify(msg)