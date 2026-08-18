from cvlab.devices import Arm, SolidDispenser, Mixer, Capper, PHMeter, SyringePump, TopCarousel, BottomCarousel, Echem, Camera, ToledoPhMeter, PotentiostatClient
from cvlab.utils.config import load_config
import os
import time 
from pathlib import Path
from flask import jsonify
import json
import sys
from math import trunc
import re
import requests
import pandas as pd
from io import StringIO
from PIL import Image
import matplotlib.pyplot as plt
from io import BytesIO


CWD_PATH = os.getcwd()
CONF_PATH = Path(os.getcwd()+'/../data/conf/devices_urls.json') 
PHMETER_CALIBRATION_CONF = Path(os.getcwd()+"/../data/calibration/ph_calibration.json")
TOP_CAROUSEL_CONF = Path(os.getcwd()+"/../data/routines/top_carousel/top_carousel.json")
BOTTOM_CAROUSEL_CONF = Path(os.getcwd()+"/../data/routines/bottom_carousel/bottom_carousel.json")
ARM_ROUTINES_PATH = Path(os.getcwd()+"/../data/routines/arm/")
ECHEM_ROUTINES_PATH = Path(os.getcwd()+"/../data/routines/echem")
POTENTIOSTATS_URL = "http://192.168.0.142:8080/api/v1/potentiostat"


liquid = {
        "liquid_id": "water",
        "volume": 1000, #uL
        "source_port": "I1",
        "destination_port": "O1",   
        "waste_port": "O3"
}

#Experiment 
experiment= {
             'name': "Ferrocyanide",
             'experimenter': "FMG",
             'experiment_type': "Cyclic Voltammetry",
             'optimisation': False,
             'polishing': False,
             'bottom_carousel_slot': 0,
             'echem_slot': 1,
             'mixer_slot':1,
             'batch': 0,
             'sample': 0,
             'working_electrode': "gold",
             'reference_electrode': "AgCL",
             'counter_Electrode': "glassy carbon",
             'ph_before':0,
             'ph_after':0,
             'cv_results':[],
             'analite':
                {
                 "sample_id": "ferrocyanide",
                 "mass_mg": 5.0,
                 "cartridge_pos": 2
                },
             'salt':
                {
                 "sample_id": "KCL",
                 "mass_mg": 5.0,
                 "cartridge_pos": 1
                },
             'liquid':
                {
                "liquid_id": "water",
                "volume": 10,
                "source_port": "I1",
                "destination_port": "O1",   
                "waste_port": "O3"
                },
             'WE_photo_be': "",
             'WE_photo_ae': "",
             }

##DEVICES INITIALISATION##

config = load_config(conf_file=CONF_PATH)

arm = Arm(
        name="Arm", 
        arm_url=config.ARM_URL, 
        arm_aux_url=config.PLC_URL, 
        arm_aux_port=config.PLC_PORT)
echem = Echem(
        name="Echem", 
        echem_url=config.ECHEM_URL, 
        echem_aux_url=config.ECHEM_AUX_URL, 
        echem_aux_port=config.ECHEM_AUX_PORT,
        pipette_url=config.PIPETTE_URL, 
        pipette_aux_url=config.PIPETTE_AUX_URL,
        pipette_aux_port=config.PIPETTE_AUX_PORT, 
        plc_url=config.PLC_URL,
        plc_port=config.PLC_PORT)
capper = Capper(
        name="Capper",
        capper_url=config.PLC_URL,
        capper_port=config.PLC_PORT)
mixer = Mixer(
        name="Mixer",
        mixer_url=config.PLC_URL,
        mixer_port=config.PLC_PORT,
        mixer_aux_url=config.PUMPS_URL,
        mixer_aux_port=config.PUMPS_PORT)
solids_dispenser = SolidDispenser(
        name="Quantos",
        solid_dispenser_url=config.SOLIDS_URL,
        solid_dispenser_aux_url=config.PLC_URL,
        solid_dispenser_aux_port=config.PLC_PORT)

liquids_dispenser = SyringePump(
            name="Liquids Pump",
            syringe_pump_url=config.LIQUIDS_URL,
            syringe_pump_aux_url=config.PLC_URL,
            syringe_pump_aux_port=config.PLC_PORT
        )
top_carousel = TopCarousel(
    name="Top Carousel",
    carousel_url=config.TOP_CAROUSEL_URL,
    carousel_port=config.TOP_CAROUSEL_URL,
    conf_file=TOP_CAROUSEL_CONF
)
bottom_carousel = BottomCarousel(
    name="Bottom Carousel",
    carousel_url=config.BOTTOM_CAROUSEL_URL,
    carousel_port=config.BOTTOM_CAROUSEL_PORT,
    aux_carousel_pump_url=config.PUMPS_URL,
    aux_carousel_pump_port=config.PUMPS_URL,
    aux_carousel_purger_url=config.PLC_URL,
    aux_carousel_purger_port=config.PLC_PORT,
    conf_file=BOTTOM_CAROUSEL_CONF
)
ph_toledo_meter = ToledoPhMeter(
            name="EasyPluspHmeter", 
            toledophmeter_url=config.TOLEDO_PH_METER_URL, 
            servo_url=config.SERVO_URL, 
            servo_port=config.SERVO_PORT)
# ---------------------------------------------------
# Helpers General
# ---------------------------------------------------

def run_cyclic_voltammetry(
    potentiostat_id=2,
    i_range=5,
    start_potential=0,
    potential_vertex=1,
    scan_rate=100,
    cycles=1,
    increment=0.01,
    show_plot=True,
):
    """
    Ejecuta una medición de Cyclic Voltammetry.

    Retorna:
        df : pandas.DataFrame
        data : list[dict]
    """

    endpoint = f"{POTENTIOSTATS_URL}/{potentiostat_id}/cyclic_voltammetry"
    plot_endpoint = f"{POTENTIOSTATS_URL}/{potentiostat_id}/cyclic_voltammetry/plot"

    params = {
        "i_range": i_range,
        "start_potential": start_potential,
        "potential_vertex": potential_vertex,
        "scan_rate": scan_rate,
        "cycles": cycles,
        "increment": increment,
    }

    # Ejecutar medición
    response = requests.post(endpoint, params=params)
    response.raise_for_status()

    # Leer CSV
    csv_text = response.text
    df = pd.read_csv(StringIO(csv_text))

    # Convertir a lista de diccionarios
    data = df.to_dict(orient="records")

    # Descargar imagen
    img_response = requests.get(plot_endpoint)
    img_response.raise_for_status()

    if show_plot:
        img = Image.open(BytesIO(img_response.content))

        plt.figure(figsize=(6,4))
        plt.imshow(img)
        plt.axis("off")
        plt.show()

    return df, data

def truncate_float(number, digits):
    factor = 10 ** digits
    return trunc(number * factor) / factor

def load_arm_routine(name):

    path = os.path.join(ARM_ROUTINES_PATH, name)

    if not os.path.isfile(path):

        print("[ERROR] Arm routines not found.")

    try:

        with open(path, "r") as f:
            data = json.load(f)

        gcodes = data.get("GCODES", [])

        return gcodes

    except Exception as e:
        print(F"[ERROR] {e}")
        return
    
def load_echem_routine(name):

    path = os.path.join(ECHEM_ROUTINES_PATH, name)

    if not os.path.isfile(path):

        print("[ERROR] Arm routines not found.")

    try:

        with open(path, "r") as f:
            data = json.load(f)

        gcodes = data.get("GCODES", [])

        return gcodes

    except Exception as e:
        print(F"[ERROR] {e}")
        return
# ---------------------------------------------------
# Helpers Arm
# ---------------------------------------------------

def get_current_position_arm():
    """
    Reads current XYZ position from robot status.
    """

    status = arm.status()["response"]

    X = truncate_float(float(status.split("X")[1].split("Y")[0]), 3)
    Y = truncate_float(float(status.split("Y")[1].split("Z")[0]), 3)
    Z = truncate_float(float(status.split("Z")[1].split("GRIPPER")[0]), 3)

    return X, Y, Z


def extract_axis_arm(gcode, axis):
    """
    Extract axis from GCODE.

    Example:
        extract_axis("G1 X10 Y20", "X")
    """

    match = re.search(rf"{axis}(-?\d+\.?\d*)", gcode)

    if match:
        return float(match.group(1))

    return None


def ensure_feedrate_arm(gcode, default_feedrate=500):
    """
    Automatically add feedrate if missing.
    """

    if gcode.startswith("G1") and "F" not in gcode:
        gcode += f" F{default_feedrate}"

    return gcode


def update_cached_position_arm(gcode):
    """
    Updates cached arm coordinates from G1 commands.
    """

    if not gcode.startswith("G1"):
        return

    x = extract_axis_arm(gcode, "X")
    y = extract_axis_arm(gcode, "Y")
    z = extract_axis_arm(gcode, "Z")

    if x is not None:
        arm.X_axis = truncate_float(x, 3)

    if y is not None:
        arm.Y_axis = truncate_float(y, 3)

    if z is not None:
        arm.Z_axis = truncate_float(z, 3)


def process_special_commands_arm(gcode):
    """
    Handles custom M commands.
    """

    command = gcode.strip()

    if command == "M100":
        arm.open_gripper()

        return {
            "ok": True,
            "message": "[INFO] Gripper open"
        }

    elif command == "M200":
        arm.close_gripper()

        return {
            "ok": True,
            "message": "[INFO] Gripper closed"
        }

    return None


def send_robot_gcode_arm(gcode):
    """
    Centralized GCODE handler.

    Features:
    - Handles M100/M200
    - Injects feedrate automatically
    - Updates cached XYZ
    """

    # Handle custom commands first
    special = process_special_commands_arm(gcode)

    if special:
        return special

    # Ensure feedrate exists
    gcode = ensure_feedrate_arm(gcode)

    # Send to robot
    response = arm.send_gcode(gcode)

    #print(response)

    # Update cached XYZ
    update_cached_position_arm(gcode)
    return response

def execute_routine_arm(routine):
    gcodes = load_arm_routine(routine)
    for gcode in gcodes:
        send_robot_gcode_arm(gcode);arm.wait_until_idle()
        time.sleep(0.5)
def home_arm():
    arm.home();arm.wait_until_idle()
    arm.home();arm.wait_until_idle()
    arm.home();arm.wait_until_idle()
    arm.X_axis = 0.0
    arm.Y_axis = 0.0
    arm.Z_axis = 0.0

# ---------------------------------------------------
# Helpers echem TODO
# ---------------------------------------------------

def get_current_position_echem():
    """
    Reads current XYZ position from robot status.
    """

    msg = echem.status()
    pattern = r"X(?P<X>-?\d+(?:\.\d+)?)Y(?P<Y>-?\d+(?:\.\d+)?)Z(?P<Z>-?\d+(?:\.\d+)?)"
    match = re.search(pattern, msg["response"])
    if match:
        X = truncate_float(float(match.group("X")),3)
        Y = truncate_float(float(match.group("Y")),3)
        Z = truncate_float(float(match.group("Z")),3)

    return X, Y, Z


def extract_axis_echem(gcode, axis):
    """
    Extract axis from GCODE.

    Example:
        extract_axis("G1 X10 Y20", "X")
    """

    match = re.search(rf"{axis}(-?\d+\.?\d*)", gcode)

    if match:
        return float(match.group(1))

    return None


def ensure_feedrate_echem(gcode, default_feedrate=500):
    """
    Automatically add feedrate if missing.
    """

    if gcode.startswith("G1") and "F" not in gcode:
        gcode += f" F{default_feedrate}"

    return gcode


def update_cached_position_echem(gcode):
    """
    Updates cached arm coordinates from G1 commands.
    """

    if not gcode.startswith("G1"):
        return

    x = extract_axis_echem(gcode, "X")
    y = extract_axis_echem(gcode, "Y")
    z = extract_axis_echem(gcode, "Z")

    if x is not None:
        echem.X_axis = truncate_float(x, 3)

    if y is not None:
        echem.Y_axis = truncate_float(y, 3)

    if z is not None:
        echem.Z_axis = truncate_float(z, 3)


def process_special_commands_echem(gcode):
    """
    Handles custom M commands.
    """

    command = gcode.strip()

    if command == "M101":
        echem.raise_electrodes()

        return {
            "ok": True,
            "message": "[INFO] Electrodes raised"
        }

    elif command == "M201":
        echem.lower_electrodes()

        return {
            "ok": True,
            "message": "[INFO] Electrodes lowered"
        }

    return None


def send_robot_gcode_echem(gcode):
    """
    Centralized GCODE handler.

    Features:
    - Handles M10n/M20n
    - Injects feedrate automatically
    - Updates cached XYZ
    """

    # Handle custom commands first
    special = process_special_commands_echem(gcode)

    if special:
        return special

    # Ensure feedrate exists
    gcode = ensure_feedrate_echem(gcode)

    # Send to robot
    response = echem.send_gcode(gcode)

    #print(response)

    # Update cached XYZ
    update_cached_position_echem(gcode)

    return response


def home_echem():
    echem.home();echem.wait_until_idle()
    echem.X_axis = 0.0
    echem.Y_axis = 0.0
    echem.Z_axis = 0.0

def execute_routine_echem(routine):
    gcodes = load_echem_routine(routine)
    for gcode in gcodes:
        send_robot_gcode_echem(gcode);echem.wait_until_idle()
        time.sleep(0.5)

if __name__ == "__main__":
    #############################
    # Testing mixer
    ############################
    #############################
    # Electrolite preparation workflow
    ############################
    print(F"[INFO] Script running in...{CWD_PATH}")
    print("[INFO] Starting ferrocyanide workflow...")
    print("[INFO] Homing arm")
    home_arm()
    print("[INFO] Homing echem")
    home_echem()
    print("[INFO] Homing bottom carousel")
    bottom_carousel.home();time.sleep(10)
    print("[INFO] Moving bottom carousel to position 0")
    bottom_carousel.move_absolute(str(0));time.sleep(10)
    #####TESTED SAMPLING PREPARATION!!!
    print("[INFO] Move robot to idle position.")
    execute_routine_arm("idle.json")
    print("[INFO] Opening quantos door")
    solids_dispenser.open_side_doors()
    solids_dispenser.open_front_door();time.sleep(3)
    print("[INFO] Moving vial to quantos.")
    execute_routine_arm("pick_vial_from_bottom_carousel.json")
    #execute_routine_arm("idle.json")
    execute_routine_arm("place_vial_in_quantos.json")
    #home_arm()
    #execute_routine_arm("idle.json")
    print(F"[INFO] Inserting cartridge number {experiment['salt']['cartridge_pos']} with {experiment['salt']['sample_id']} in quantos.")
    execute_routine_arm(F"pick_cartridge_from_tower_{experiment['salt']['cartridge_pos']}.json")
    execute_routine_arm("idle.json")
    print("[INFO] Closing quantos doors.")
    solids_dispenser.close_side_doors()
    solids_dispenser.close_front_door();time.sleep(5)
    print("[INFO] Dispensing...");time.sleep(5)
    #dispensing TODO
    print("[INFO] Opening quantos doors.")
    solids_dispenser.open_side_doors()
    solids_dispenser.open_front_door();time.sleep(3)
    
    ###**
    print(F"[INFO] Returning cartridge number {experiment['salt']['cartridge_pos']} with {experiment['salt']['sample_id']} to tower.")
    execute_routine_arm(F"place_cartridge_in_tower_{experiment['salt']['cartridge_pos']}.json")
    print(F"[INFO] Inserting cartridge number {experiment['analite']['cartridge_pos']} with {experiment['analite']['sample_id']} in quantos.")
    execute_routine_arm(F"pick_cartridge_from_tower_{experiment['analite']['cartridge_pos']}.json")
    execute_routine_arm("idle.json")
    print("[INFO] Closing quantos doors.")
    solids_dispenser.close_side_doors()
    solids_dispenser.close_front_door();time.sleep(5)
    print("[INFO] Dispensing.");time.sleep(5)
    #set antiestatic on
    #tare
    #dispensing TODO
    #get weight
    #set antiestatic off
    print("[INFO] Opening quantos doors.")
    solids_dispenser.open_side_doors()
    solids_dispenser.open_front_door();time.sleep(3)
    print(F"[INFO] Returning cartridge number {experiment['analite']['cartridge_pos']} with {experiment['salt']['sample_id']} to tower.")
    execute_routine_arm(F"place_cartridge_in_tower_{experiment['analite']['cartridge_pos']}.json")
    print("[INFO] Moving vial to capper.")
    execute_routine_arm("pick_vial_from_quantos.json")
    #ROBOT PLACES VIAL IN CAPPER
    execute_routine_arm("place_vial_in_capper.json")
    print("[INFO] ispensing liquid.")
    capper.hold_vial()
    ####
    #LIQUID DISPENSING TODO
    print("[INFO] Testing pump..")
    print(liquids_dispenser.status());time.sleep(0.3)
    print(liquids_dispenser.get_valve_pos());time.sleep(0.3)
    print(liquids_dispenser.dispense(liquid));time.sleep(0.3)
    print(liquids_dispenser.move_home());time.sleep(0.3)
    ####
    liquids_dispenser.piston_to_dispense_position();time.sleep(5)
    #prime lines 
    #dispense
    liquids_dispenser.piston_to_home_position()
    ####
    capper.release_vial()
    print("[INFO] Moving vial to mixer.")
    execute_routine_arm("pick_vial_from_capper.json")
    execute_routine_arm("place_vial_in_mixer_1.json")
    execute_routine_arm("idle.json")
    print("[INFO] Mixing.")
    mixer.lower_lift();time.sleep(10)
    mixer.turn_ultrasound_bath_on();time.sleep(5)
    mixer.turn_ultrasound_bath_off()
    mixer.raise_lift()
    print("[INFO] Moving vial to bottom carousel.")
    execute_routine_arm("pick_vial_from_mixer_1.json")
    execute_routine_arm("idle.json")
    execute_routine_arm("place_vial_in_bottom_carousel.json")
    execute_routine_arm("idle.json")
    home_arm()
    #######################
    # Sample analysis
    ###################
    
    #ROBOT MOVES RACK TO ECHEM's slot 1 TESTED
    print("[INFO] Moving rack to echem.")
    execute_routine_arm("pick_rack_from_bottom_carousel.json")
    execute_routine_arm("place_rack_in_1.json")
    # PH
    print("[INFO] Setting ph measurement.") 
    execute_routine_echem("ph_measurement.json")
    print("[INFO] Picking ph Probe") 
    execute_routine_arm("pick_ph_probe.json")
    print("[INFO] Measuring ph in rack 1") 
    execute_routine_arm("measure_ph_in_rack_1.json")
    #Ph 
    ph_toledo_meter.press_read_button();time.sleep(3)
    msg = ph_toledo_meter.read_ph();time.sleep(2)
    ph_before = msg['pH']
    print(F"[INFO] Measurement done: {ph_before}") 
    #
    print("[INFO] Measurement done.") 
    execute_routine_arm("measure_ph_in_rack_1_out.json")
    print("[INFO] Washing ph probe.") 
    execute_routine_arm("wash_ph_probe_be_in_rack_1.json")
    print("[INFO] Returning ph probe") 
    execute_routine_arm("place_ph_probe.json")
    execute_routine_echem("idle.json")
    home_echem()
    ###
    print("[INFO] Washing electrodes.") 
    execute_routine_echem("wash_electrodes.json")
    execute_routine_echem("ph_measurement.json")
    print("[INFO] Drying electrodes") 
    echem.dryer_on();time.sleep(2)
    echem.dryer_off();time.sleep(1)
    execute_routine_echem("idle.json")
    #PHOTO BEFORE EXPERIMENT OF ELECTRODES TODO
    print("[INFO] Sinking electrodes in cell.") 
    execute_routine_echem("cv_start_position.json")
    print("[INFO]  Executing CV test...")
    df, data = run_cyclic_voltammetry()
    print("[INFO] CV test done.") 
    execute_routine_echem("cv_end_position.json")
    execute_routine_echem("idle.json")
    home_echem()
    ##PH
    print("[INFO] Setting ph measurement.") 
    execute_routine_echem("ph_measurement.json")
    print("[INFO] Picking ph Probe") 
    execute_routine_arm("pick_ph_probe.json")
    print("[INFO] Measuring ph in rack 1") 
    execute_routine_arm("measure_ph_in_rack_1.json")
    #Ph 
    ph_toledo_meter.press_read_button();time.sleep(3)
    msg = ph_toledo_meter.read_ph();time.sleep(2)
    ph_after = msg['pH']
    print(F"[INFO] Measurement done: {ph_after}") 
    #
    execute_routine_arm("measure_ph_in_rack_1_out.json")
    print("[INFO] Washing ph probe.") 
    execute_routine_arm("wash_ph_probe_ae_in_rack_1.json")
    print("[INFO] Returning ph probe") 
    execute_routine_arm("place_ph_probe.json")
    execute_routine_echem("idle.json")
    #PHOTO OF ELECTRODES AFTER EXPERIMENT
    home_echem()
    ##
    #AI GENERATES REPORT TODO
    #PHOTO of ELECTRODE TODO
    print("[INFO] Returning rack to carousel.")
    execute_routine_arm("idle.json")
    execute_routine_arm("pick_rack_from_1.json")
    execute_routine_arm("place_rack_in_bottom_carousel.json")
    #POLISHING? YES POLISH no? continue TODO
    print("[INFO] Workflow finished, homing arm.")
    home_arm()
    
