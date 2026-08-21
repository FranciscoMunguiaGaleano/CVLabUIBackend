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
import math


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
        plc_port=config.PLC_PORT,
        stirrer_url=config.STIRRER_URL,
        stirrer_port=config.STIRRER_PORT)  
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
    potentiostat_id=1,
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
        #time.sleep(0.5)
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
        #time.sleep(0.5)

def semicircle_g1(start, end, direction=1, segments=20, feed=500):
    """
    Dibuja un semicírculo desde start hasta end usando solamente G1.

    start/end: (x, y, z)
    direction:
        1  -> semicírculo por un lado
        -1 -> semicírculo por el otro lado
    segments: número de pequeños segmentos
    """

    x1, y1, z = start
    x2, y2, _ = end

    # Centro del círculo = punto medio entre start y end
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    # Radio
    radius = math.sqrt((x2 - x1)**2 + (y2 - y1)**2) / 2

    # Ángulo inicial
    start_angle = math.atan2(y1 - cy, x1 - cx)

    # Semicírculo = 180 grados
    angle_step = direction * math.pi / segments

    for i in range(1, segments + 1):
        angle = start_angle + angle_step * i

        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)

        gcode = f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f} F{feed}"

        #print(gcode)
        send_robot_gcode_echem(gcode)
        #echem.wait_until_idle()

def polish_electrode(electrode_id=1, passes = 10):
    '''
    electrode_id 1 to 3 available
    '''
    print(F"[INFO] Polishing electrode {electrode_id} for {passes} passes.")
    E_OFFS = {
            1:[0,0,20],
            2:[50,0,20],
            3:[100,0,49.5]
        }
    x_offset=E_OFFS[electrode_id][0]
    y_offset=E_OFFS[electrode_id][1]
    z_offset=E_OFFS[electrode_id][2]
    print("[INFO] Homing echem...")
    home_echem();echem.wait_until_idle()
    p1 = (5+x_offset, 1.0+y_offset, 0.0+z_offset)
    p2 = (8+x_offset, 6.0+y_offset, 0.0+z_offset)
    p3 = (5+x_offset, 6.0+y_offset, 0.0+z_offset)
    p4 = (8+x_offset, 1.0+y_offset, 0.0+z_offset)
    #below the electrode
    print(F"[INFO] Moving polishing disc below electrode {electrode_id}")
    gcode = f"G1 X{p2[0]} Y{p2[1]} Z{p2[2]-2} F500"
    send_robot_gcode_echem(gcode);echem.wait_until_idle()
    #touching the electrode
    print(F"[INFO] Approaching polishing disc towards electrode {electrode_id}")
    gcode = f"G1 X{p2[0]} Y{p2[1]} Z{p2[2]} F500"
    send_robot_gcode_echem(gcode);echem.wait_until_idle()
    for pass_n in range(0, passes):
        print(f"[INFO] Polishing eelectrode pass number: {pass_n+1}")
        # P1 -> P2
        gcode = f"G1 X{p2[0]} Y{p2[1]} Z{p2[2]} F500"
        send_robot_gcode_echem(gcode)
        #echem.wait_until_idle()
        # P2 -> P3 semicircle
        semicircle_g1(p2, p3, direction=1, segments=10)
        # P3 -> P4
        gcode = f"G1 X{p4[0]} Y{p4[1]} Z{p4[2]} F500"
        send_robot_gcode_echem(gcode)
        #echem.wait_until_idle()
        # P4 -> P1 semicircle
        semicircle_g1(p4, p1, direction=-1, segments=10)
        echem.wait_until_idle()
    #time.sleep(2)
    print(F"[INFO] Moving polishing disc below electrode {electrode_id}")
    gcode = f"G1 X{p1[0]} Y{p1[1]} Z{p1[2]-2} F500"
    send_robot_gcode_echem(gcode);echem.wait_until_idle()
    print(F"[INFO] Polishing routine of electrode {electrode_id} finished")
    home_echem();echem.wait_until_idle()
def wash_electrodes(cycles=20,electrode_id=1):
    TIMES ={
            1:[1,1,1,1],
            2:[1,1,1,1],
            3:[1,1,1,1]
        }
    print(F"[INFO] Washing electrodes for {cycles} cycles")
    echem.turn_washers_on()
    time.sleep(TIMES[electrode_id][0])
    echem.turn_washers_off()
    time.sleep(TIMES[electrode_id][1])
    for cycle in range(0,cycles):
        echem.turn_washers_on()
        time.sleep(TIMES[electrode_id][2])
        echem.turn_washers_off()
        time.sleep(TIMES[electrode_id][3])
    print("[INFO] Washing electrodes cycle finished.")

def stirr_samples(cycles=20,sample_slot_id=1):
    TIMES ={
        1:[1.5,1,1.2,1],
        2:[1.1,1.1,0.8,1.4],
        3:[1.1,1,1,1]
    }
    print(F"[INFO] Stirring samples for {cycles} cycles")
    echem.turn_stirrers_on()
    time.sleep(TIMES[sample_slot_id][0])
    echem.turn_stirrers_off()
    time.sleep(TIMES[sample_slot_id][1])
    for cycle in range(0,cycles):
        echem.turn_stirrers_on()
        time.sleep(TIMES[sample_slot_id][2])
        echem.turn_stirrers_off()
        time.sleep(TIMES[sample_slot_id][3])
    print("[INFO] Stirring samples cycle finished.")

def fill_washing_vials(carousel_slot=1):
    print(F"[INFO] Filling vials of carousel slot {carousel_slot}")

def photograph_electrode(electrode_id=1):
    return

def prime_lines(source_port=1):
    return

def degassing_sample(degassing_time=5):
    print(F"[INFO] Degassing sample for {degassing_time} seconds")
    echem.purger_on();time.sleep(degassing_time)
    echem.purger_off();time.sleep(0.1)
    print(F"[INFO] Degassing completed")
    return

def prepare_sample(
        carousel_slot=0, 
        solids={1:["NaCl",10, "Salt"],2:["Ferrocinade",1, "Analite"]}, 
        liquids={1:["Water",10, "Solvent"]},
        mix_ultrasound=False, 
        mixing_time=60):
    #############################
    # Electrolite preparation workflow introduction
    ############################
    print(F"[INFO] Preparing an electrolite from carousel slot {carousel_slot} with: ")
    for key in solids:
        print(F"[INFO] {solids[key][1]} mg of {solids[key][0]}")
    print("[INFO] and")
    for key in liquids:
        print(F"[INFO] {liquids[key][1]} mL of {liquids[key][0]}")
    print("[INFO] Homing arm")
    if mix_ultrasound:
        print(F"[INFO] Mixing sample in ultrasound bath for {mixing_time} seconds")
    home_arm()
    print("[INFO] Homing echem")
    home_echem()
    print("[INFO] Homing bottom carousel")
    bottom_carousel.home();time.sleep(10)
    print(F"[INFO] Moving bottom carousel to position {carousel_slot}")
    bottom_carousel.move_absolute(str(carousel_slot));time.sleep(10)
    #####################################
    # Filling washing vials
    #####################################
    fill_washing_vials(carousel_slot=carousel_slot)
    ##################################
    # Viel in quantos
    #####################################
    print("[INFO] Move robot to idle position.")
    execute_routine_arm("idle.json")
    print("[INFO] Opening quantos door")
    solids_dispenser.open_side_doors()
    solids_dispenser.open_front_door();time.sleep(3)
    print("[INFO] Moving vial to quantos.")
    execute_routine_arm("pick_vial_from_bottom_carousel.json")
    execute_routine_arm("place_vial_in_quantos.json")
    #####################################
    # Solids dispensing TODO put in a for loop
    #####################################
    print(F"[INFO] Inserting cartridge number {experiment['salt']['cartridge_pos']} with {experiment['salt']['sample_id']} in quantos.")
    execute_routine_arm(F"pick_cartridge_from_tower_{experiment['salt']['cartridge_pos']}.json")
    execute_routine_arm("idle.json")
    print("[INFO] Closing quantos doors.")
    solids_dispenser.close_side_doors()
    solids_dispenser.close_front_door();time.sleep(5)
    print("[INFO] Dispensing...");time.sleep(5)
    #set antiestatic on
    #tare
    #dispensing TODO
    #get weight
    #set antiestatic off
    print("[INFO] Opening quantos doors.")
    solids_dispenser.open_side_doors()
    solids_dispenser.open_front_door();time.sleep(3)
    print(F"[INFO] Returning cartridge number {experiment['salt']['cartridge_pos']} with {experiment['salt']['sample_id']} to tower.")
    execute_routine_arm(F"place_cartridge_in_tower_{experiment['salt']['cartridge_pos']}.json")
    ###Loop 2
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
    ###################################
    #LIQUID DISPENSING TODO
    ###################################
    print("[INFO] Moving vial to capper.")
    execute_routine_arm("pick_vial_from_quantos.json")
    execute_routine_arm("place_vial_in_capper.json")
    print("[INFO] Dispensing liquid.")
    capper.hold_vial()
    print("[INFO] Testing pump..")
    print(liquids_dispenser.status());time.sleep(0.3)
    print(liquids_dispenser.get_valve_pos());time.sleep(0.3)
    print(liquids_dispenser.dispense(liquid));time.sleep(0.3)
    print(liquids_dispenser.move_home());time.sleep(0.3)
    ####
    prime_lines(source_port=1)
    liquids_dispenser.piston_to_dispense_position();time.sleep(5)
    #dispense
    liquids_dispenser.piston_to_home_position()
    ####
    capper.release_vial()
    execute_routine_arm("pick_vial_from_capper.json")
    ######################################
    # Mixing
    ######################################
    if mix_ultrasound:
        print("[INFO] Moving vial to mixer.")
        execute_routine_arm("place_vial_in_mixer_2.json")
        execute_routine_arm("idle.json")
        print("[INFO] Mixing.")
        mixer.lower_lift();time.sleep(10)
        mixer.turn_ultrasound_bath_on();time.sleep(mixing_time)
        mixer.turn_ultrasound_bath_off()
        mixer.raise_lift()
        execute_routine_arm("pick_vial_from_mixer_1.json")
    #######################################
    # Sample to carousel
    #######################################
    print("[INFO] Moving vial to bottom carousel.")
    execute_routine_arm("idle.json")
    execute_routine_arm("place_vial_in_bottom_carousel.json")
    execute_routine_arm("idle.json")
    home_arm()

def analise_sample(echem_slot=1, experiment_path="", mixing = True):
    ########################################
    # Moving rack from carousel to echem
    ########################################
    print("[INFO] Moving rack to echem.")
    execute_routine_arm("pick_rack_from_bottom_carousel.json")
    execute_routine_arm(F"place_rack_in_{echem_slot}.json")
    ########################################
    # mixing
    ########################################
    if mixing:
        stirr_samples(cycles=10)
    #########################################
    # Degassing samples before Ph measurement
    ########################################
    # home_echem()
    # execute_routine_echem("idle.json")
    ########################################
    # Measuring Ph
    ########################################
    print("[INFO] Setting ph measurement.") 
    execute_routine_echem("ph_measurement.json")
    print("[INFO] Picking ph Probe") 
    execute_routine_arm("pick_ph_probe.json")
    print(F"[INFO] Measuring ph in rack {echem_slot}") 
    execute_routine_arm(F"measure_ph_in_rack_{echem_slot}.json")
    stirr_samples(cycles=20,sample_slot_id=echem_slot)
    ph_toledo_meter.press_read_button();time.sleep(3)
    msg = ph_toledo_meter.read_ph();time.sleep(2)
    ph_before = msg['pH']
    print(F"[INFO] Measurement done: {ph_before}") 
    execute_routine_arm(F"measure_ph_in_rack_{echem_slot}_out.json")
    ########################################
    # Washing Ph probe
    ########################################
    print("[INFO] Washing ph probe.") 
    execute_routine_arm(f"wash_ph_probe_be_in_rack_{echem_slot}.json")
    print("[INFO] Returning ph probe") 
    execute_routine_arm("place_ph_probe.json")
    execute_routine_echem("idle.json")
    home_echem()
    ########################################
    # Washing  Electrodes
    ########################################
    print("[INFO] Washing electrodes.") 
    execute_routine_echem("wash_electrodes.json")
    wash_electrodes(cycles=20,electrode_id=echem_slot)#TODO aqui se hay que dejarlo arriba
    execute_routine_echem("wash_electrodes_out.json")
    execute_routine_echem("ph_measurement.json")
    print("[INFO] Drying electrodes") 
    echem.dryer_on();time.sleep(2)
    echem.dryer_off();time.sleep(0.1)
    execute_routine_echem("idle.json")
    ###########################################
    #PHOTO BEFORE EXPERIMENT OF ELECTRODES TODO rutinas guardarlas y guardar foto 
    ###########################################
    print("[INFO] Sinking electrodes in cell.") 
    execute_routine_echem("cv_start_position.json")
    degassing_sample(degassing_time=5)
    ###########################################
    # CV Test TODO add Try catch blocks and repeat if there is a problem
    ###########################################
    try:
        print("[INFO]  Executing CV test...")
        df, data = run_cyclic_voltammetry(
            potentiostat_id=echem_slot,
            i_range=5,
            start_potential=0,
            potential_vertex=1,
            scan_rate=100,
            cycles=1,
            increment=0.01,
            show_plot=True,)
        print("[INFO] CV test done.") 
    except:
        print("[Error] not possible to connect with potentiostats")
    execute_routine_echem("cv_end_position.json")
    execute_routine_echem("idle.json")
    home_echem()
    #############################################
    # measruing Ph after the test
    #############################################
    print("[INFO] Setting ph measurement.") 
    execute_routine_echem("ph_measurement.json")
    print("[INFO] Picking ph Probe") 
    execute_routine_arm("pick_ph_probe.json")
    print(F"[INFO] Measuring ph in rack {echem_slot}") 
    execute_routine_arm(F"measure_ph_in_rack_{echem_slot}.json")
    stirr_samples(cycles=20,sample_slot_id=1)
    ph_toledo_meter.press_read_button();time.sleep(3)
    msg = ph_toledo_meter.read_ph();time.sleep(2)
    ph_after = msg['pH']
    print(F"[INFO] Measurement done: {ph_after}") 
    execute_routine_arm(F"measure_ph_in_rack_{echem_slot}_out.json")
    print("[INFO] Washing ph probe.") 
    execute_routine_arm(F"wash_ph_probe_ae_in_rack_{echem_slot}.json")
    print("[INFO] Returning ph probe") 
    execute_routine_arm("place_ph_probe.json")
    execute_routine_echem("idle.json")
    #############################################
    # Photo of electrode after the test TODO
    #############################################
    home_echem()
    #############################################
    #AI GENERATES REPORT TODO
    #############################################
    #############################################
    # Homing system
    #############################################
    print("[INFO] Returning rack to carousel.")
    execute_routine_arm("idle.json")
    execute_routine_arm("pick_rack_from_1.json")
    execute_routine_arm("place_rack_in_bottom_carousel.json")
    ##############################################
    #POLISHING? YES POLISH no? continue TODO
    ##############################################
    while True:
        answer=input(f'[WARNING] Polihs electrode {echem_slot} (y/n)')
        if answer == 'y' or answer == 'Y':
            print(F"[INFO] Polishing electrode {echem_slot} ")
            polish_electrode(electrode_id=3,passes=3)
            #washing and drying routine again
            break
        elif answer == 'n' or answer == 'N':
            print(F"[WARNING] Electrode {echem_slot} not polished.")
            break
    print("[INFO] Workflow finished, homing arm.")
    home_arm()

if __name__ == "__main__":
    print(F"[INFO] Script running in...{CWD_PATH}")
    print("[INFO] Starting ferrocyanide workflow...")
    #prepare_sample()
    #home_arm()
    #analise_sample()
    echem_slot=1
    print("[INFO] Washing ph probe.") 
    execute_routine_arm(F"wash_ph_probe_ae_in_rack_{echem_slot}.json")
    print("[INFO] Returning ph probe") 
    execute_routine_arm("place_ph_probe.json")
    execute_routine_echem("idle.json")
    #############################################
    # Photo of electrode after the test TODO
    #############################################
    home_echem()
    #############################################
    #AI GENERATES REPORT TODO
    #############################################
    #############################################
    # Homing system
    #############################################
    print("[INFO] Returning rack to carousel.")
    execute_routine_arm("idle.json")
    execute_routine_arm("pick_rack_from_1.json")
    execute_routine_arm("place_rack_in_bottom_carousel.json")
    ##############################################
    #POLISHING? YES POLISH no? continue TODO
    ##############################################
    while True:
        answer=input(f'[WARNING] Polihs electrode {echem_slot} (y/n)')
        if answer == 'y' or answer == 'Y':
            print(F"[INFO] Polishing electrode {echem_slot} ")
            polish_electrode(electrode_id=3,passes=3)
            #washing and drying routine again
            break
        elif answer == 'n' or answer == 'N':
            print(F"[WARNING] Electrode {echem_slot} not polished.")
            break
    print("[INFO] Workflow finished, homing arm.")
    home_arm()
    
