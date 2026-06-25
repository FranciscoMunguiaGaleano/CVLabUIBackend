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
def raise_lift():
    mixer.raise_lift()
    return jsonify({'message': '[INFO] Raising lift'})

@mixer_bp.route("/lower_lift", methods=["GET"])
def lower_lift():
    mixer.lower_lift()
    return jsonify({'message': '[INFO] Lowering lift'})
# ------------------------------------------------------------------
# Ultrasound bath control
# ------------------------------------------------------------------
@mixer_bp.route("/turn_ultrasound_bath_on", methods=["GET"])
def turn_ultrasound_bath_on():
    mixer.turn_ultrasound_bath_on()
    return jsonify({'message': '[INFO] Ultrasound bath is on'})
@mixer_bp.route("/turn_ultrasound_bath_off", methods=["GET"])
def turn_ultrasound_bath_off():
    mixer.turn_ultrasound_bath_off()
    return jsonify({'message': '[INFO] Ultrasound bath is off'})
    