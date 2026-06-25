from flask import Blueprint, jsonify, request
from devices.device_manager import devices
import os
import json


phmeter_toledo_bp = Blueprint("/api/v1/phmetertoledo", __name__)

phmeter_toledo = devices.ph_toledo_meter

@phmeter_toledo_bp.route("/read_status", methods=["GET"])
def read_status():
    """Read status of the pH meter (EasyPlus Toledo)."""
    msg=str(phmeter_toledo.status())
    return jsonify(msg)
    #return jsonify({"message": str(phmeter.read_status)})

@phmeter_toledo_bp.route("/read_ph", methods=["GET"])
def read_ph():
    """Read pH value, applying calibration."""
    phmeter_toledo.press_read_button()
    msg = phmeter_toledo.read_ph()
    print(msg)
    ph = msg['pH']
    temp = msg['temperature_C']
    return jsonify({"message":f"[INFO] The measured pH is {ph} and the temperature is: {temp} C"})