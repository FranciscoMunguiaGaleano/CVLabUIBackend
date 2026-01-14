from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json


mixer_bp = Blueprint("/api/v1/mixer", __name__)

mixer = devices.mixer


# ------------------------------------------------------------------
# Lift control
# ------------------------------------------------------------------
@mixer_bp.route("/raise_lift", methods=["GET"])
def raise_lift(self):
    return jsonify(mixer.raise_lift())

@mixer_bp.route("/lower_lift", methods=["GET"])
def lower_lift(self):
    return jsonify(mixer.lower_lift())
# ------------------------------------------------------------------
# Ultrasound bath control
# ------------------------------------------------------------------
@mixer_bp.route("/turn_ultrasound_bath_on", methods=["GET"])
def turn_ultrasound_bath_on(self):
    return jsonify(mixer.turn_ultrasound_bath_on())
@mixer_bp.route("/turn_ultrasound_bath_off", methods=["GET"])
def turn_ultrasound_bath_off(self):
    return jsonify(mixer.turn_ultrasound_bath_off())
    