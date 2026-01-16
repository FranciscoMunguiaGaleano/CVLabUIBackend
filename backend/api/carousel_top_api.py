from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json


top_carousel_bp = Blueprint("/api/v1/top_carousel", __name__)

top_carousel = devices.top_carousel

@top_carousel_bp.route("/home", methods=["GET"])
def home():
    """Home the carousel."""
    msg = {"message":"[INFO] Homing Top Carousel..."}
    top_carousel.home()
    return jsonify(msg)

@top_carousel_bp.route("/move_absolute", methods=["POST"])
def move_absolute():
    """Move carousel to an absolute position."""
    data = request.json or {}
    pos = data.get("pos")
    position = top_carousel.positions[str(pos)]
    print(position)
    msg = {"message": f"[INFO] Moving Top Carousel absolute position {pos} at {position} degrees"}
    top_carousel.move_absolute(str(pos))
    return jsonify(msg)

@top_carousel_bp.route("/move_incremental", methods=["POST"])
def move_incremental():
    """Move carousel by a step increment."""
    data = request.json or {}
    step = data.get("step")
    top_carousel.step = float(step)
    msg = {"message":f"[INFO] Moving Top Carousel incrementally to {top_carousel.position:.2f} degrees"}
    top_carousel.move_incremental()
    return jsonify(msg)