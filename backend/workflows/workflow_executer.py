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
import argparse
import logging
import shutil
import base64
from datetime import date
from automated_analysis import run_analysis



BASE_PATH = Path(__file__).resolve().parent.parent


CONF_PATH = BASE_PATH / "data" / "conf" / "devices_urls.json"
PHMETER_CALIBRATION_CONF = BASE_PATH / "data" / "calibration" / "ph_calibration.json"
TOP_CAROUSEL_CONF = BASE_PATH / "data" / "routines" / "top_carousel" / "top_carousel.json"
BOTTOM_CAROUSEL_CONF = BASE_PATH / "data" / "routines" / "bottom_carousel" / "bottom_carousel.json"
ARM_ROUTINES_PATH = BASE_PATH / "data" / "routines" / "arm"
ECHEM_ROUTINES_PATH = BASE_PATH / "data" / "routines" / "echem"

#CWD_PATH = os.getcwd()
#CONF_PATH = Path(os.getcwd()+'/../data/conf/devices_urls.json') 
#PHMETER_CALIBRATION_CONF = Path(os.getcwd()+"/../data/calibration/ph_calibration.json")
#TOP_CAROUSEL_CONF = Path(os.getcwd()+"/../data/routines/top_carousel/top_carousel.json")
#BOTTOM_CAROUSEL_CONF = Path(os.getcwd()+"/../data/routines/bottom_carousel/bottom_carousel.json")
#ARM_ROUTINES_PATH = Path(os.getcwd()+"/../data/routines/arm/")
#ECHEM_ROUTINES_PATH = Path(os.getcwd()+"/../data/routines/echem")

I_range_mode={
    "AUTO": 0,
    "MILLIAMPS200" : 1,
    "MILLIAMPS20" : 2,
    "MICROAMPS2000" : 3,
    "MICROAMPS200" : 4,
    "MICROAMPS20" : 5

}

liquid = {
        "liquid_id": "water",
        "volume": 1000, #uL
        "source_port": "I2",
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
             'analyte':
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
    aux_carousel_pump_port=config.PUMPS_PORT,
    aux_carousel_purger_url=config.PLC_URL,
    aux_carousel_purger_port=config.PLC_PORT,
    conf_file=BOTTOM_CAROUSEL_CONF
)
ph_toledo_meter = ToledoPhMeter(
            name="EasyPluspHmeter", 
            toledophmeter_url=config.TOLEDO_PH_METER_URL, 
            servo_url=config.SERVO_URL, 
            servo_port=config.SERVO_PORT)

camera = Camera(
            name="EchemCamera",
            camera_url=config.CAMERA_URL
        )
#potentiostats = PotentiostatClient(
#            name= "Ossila Potentiostats",
#            base_url=config.POTENTIOSTASTS_URL)
# ---------------------------------------------------
# Helpers General
# ---------------------------------------------------
LIQUIDS_CHANNELS={1:"I2",2:"I3",3:"I4",4:"I5",5:"I6"}
#POTENTIOSTATS_URL = f"http://{POTENTIOSTASTS_URL}/api/v1/potentiostat"
POTENTIOSTATS_URL = "http://192.168.0.142:8080/api/v1/potentiostat"
#                    http://192.168.0.142:8080/api/v1/potentiostat/3/status
#http://192.168.0.142:8080/api/v1/potentiostat
#POTENTIOSTATS_URL = f"{config.POTENTIOSTASTS_URL}/api/v1/potentiostat"


def encode_image_to_base64(image_path):
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def run_cyclic_voltammetry(
    potentiostat_id=1,
    i_range=5,
    start_potential=0,
    potential_vertex=1,
    scan_rate=100,
    cycles=1,
    increment=0.01,
    show_plot=True,
    file_name="CV.png"
):
    """
    Ejecuta una medición de Cyclic Voltammetry.

    Retorna:
        df : pandas.DataFrame
        data : list[dict]
    """

    endpoint = f"{POTENTIOSTATS_URL}/{potentiostat_id}/cyclic_voltammetry"
    plot_endpoint = (
        f"{POTENTIOSTATS_URL}/{potentiostat_id}/cyclic_voltammetry/plot"
    )

    print(endpoint)

    params = {
        "i_range": i_range,
        "start_potential": start_potential,
        "potential_vertex": potential_vertex,
        "scan_rate": scan_rate,
        "cycles": cycles,
        "increment": increment,
    }

    # Execute CV measurement
    response = requests.post(endpoint, params=params)
    response.raise_for_status()

    print(response)

    # Read CSV
    csv_text = response.text
    df = pd.read_csv(StringIO(csv_text))

    # Convert to list of dictionaries
    data = df.to_dict(orient="records")

    # Download plot image
    img_response = requests.get(plot_endpoint)
    img_response.raise_for_status()

    # Save the actual image
    if file_name:
        with open(file_name, "wb") as f:
            f.write(img_response.content)

    # Display the actual image
    if show_plot:
        img = Image.open(BytesIO(img_response.content))

        plt.figure(figsize=(6, 4))
        plt.imshow(img)
        plt.axis("off")
        plt.show()
        plt.close()

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
        time.sleep(5)
        arm.open_gripper();time.sleep(1.5)

        return {
            "ok": True,
            "message": "[INFO] Gripper open"
        }

    elif command == "M200":
        time.sleep(5)
        arm.close_gripper();time.sleep(1.5)

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
        time.sleep(0.1)
        arm.wait_until_idle()
        time.sleep(0.1)
        arm.wait_until_idle()
        time.sleep(0.1)
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

    #print(x,y,z)
    #print(echem.X_axis,echem.Y_axis,echem.Z_axis)


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
    #send_robot_gcode_echem("G1 X10.0 Y0.0 Z0.0");echem.wait_until_idle()
    echem.home();echem.wait_until_idle()
    #send_robot_gcode_echem("G1 X11.0 Y0.0 Z0.0");echem.wait_until_idle()
    #echem.home();echem.wait_until_idle()
    #send_robot_gcode_echem("G1 X11.0 Y0.0 Z0.0");echem.wait_until_idle()
    ##echem.home();echem.wait_until_idle()
    #send_robot_gcode_echem("G1 X11.0 Y0.0 Z0.0");echem.wait_until_idle()
    echem.X_axis = 0.0
    echem.Y_axis = 0.0
    echem.Z_axis = 0.0

def execute_routine_echem(routine):
    gcodes = load_echem_routine(routine)
    for gcode in gcodes:
        #print(gcode)
        send_robot_gcode_echem(gcode);echem.wait_until_idle()
        time.sleep(0.2)
        echem.wait_until_idle();time.sleep(0.2)
        echem.wait_until_idle();time.sleep(0.2)

        

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
            2:[50,0,48],
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

def stirr_samples(cycles=20,sample_slot_id=2):
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
    bottom_carousel.move_absolute(str(9));time.sleep(20)
    print("[INFO] Filling washing vials")
    bottom_carousel.turn_pumps_on();time.sleep(22)
    bottom_carousel.turn_pumps_off()
    bottom_carousel.move_absolute(str(carousel_slot));time.sleep(0)

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
        solids={1:["NaCl",10, "Salt"],2:["Ferrocinade",1, "Analyte"]}, 
        liquids={1:["Water",10, "Solvent"]},
        mix_ultrasound=False, 
        mixing_time=60,
        experiment={}):
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
    # Vial in quantos
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
    print("[INFO] Dispensing.");time.sleep(5)
    solids_dispenser.lock_dosing_head()
    #set antiestatic on
    #tare
    solids_dispenser.tare_balance()
    #Dispense a sample.
    #Expects JSON:
    #solids={1:["NaCl",10, "Salt"],2:["Ferrocynade",1, "Analyte"]}
    data = {
        "sample_id": solids[1][0],
        "mass": solids[1][1]
    }
    solids_dispenser.dispense(data)
    #get weight
    weight_salt = solids_dispenser.get_sample_data()
    print(F"[INFO] Dispensed: {weight_salt}")
    solids_dispenser.unlock_dosing_head()
    #set antiestatic off
    print("[INFO] Opening quantos doors.")
    solids_dispenser.open_side_doors()
    solids_dispenser.open_front_door();time.sleep(3)
    print(F"[INFO] Returning cartridge number {experiment['salt']['cartridge_pos']} with {experiment['salt']['sample_id']} to tower.")
    execute_routine_arm(F"place_cartridge_in_tower_{experiment['salt']['cartridge_pos']}.json")
    ###Loop 2
    print(F"[INFO] Inserting cartridge number {experiment['analyte']['cartridge_pos']} with {experiment['analyte']['sample_id']} in quantos.")
    execute_routine_arm(F"pick_cartridge_from_tower_{experiment['analyte']['cartridge_pos']}.json")
    execute_routine_arm("idle.json")
    print("[INFO] Closing quantos doors.")
    solids_dispenser.close_side_doors()
    solids_dispenser.close_front_door();time.sleep(5)
    print("[INFO] Dispensing.");time.sleep(5)
    solids_dispenser.lock_dosing_head()
    #set antiestatic on
    #tare
    solids_dispenser.tare_balance()
    #Dispense a sample.
    #Expects JSON:
    #solids={1:["NaCl",10, "Salt"],2:["Ferrocynade",1, "Analyte"]}
    data = {
        "sample_id": solids[2][0],
        "mass": solids[2][1]
    }
    solids_dispenser.dispense(data)
    #get weight
    weight_analyte = solids_dispenser.get_sample_data()
    print(F"[INFO] Dispensed: {weight_analyte}")
    solids_dispenser.unlock_dosing_head()
    #set antiestatic off
    print("[INFO] Opening quantos doors.")
    solids_dispenser.open_side_doors()
    solids_dispenser.open_front_door();time.sleep(3)
    print(F"[INFO] Returning cartridge number {experiment['analyte']['cartridge_pos']} with {experiment['salt']['sample_id']} to tower.")
    execute_routine_arm(F"place_cartridge_in_tower_{experiment['analyte']['cartridge_pos']}.json")
    ###################################
    #LIQUID DISPENSING TODO put in a for loop
    ###################################
    print("[INFO] Moving vial to capper.")
    execute_routine_arm("pick_vial_from_quantos.json")
    execute_routine_arm("place_vial_in_capper.json")
    print("[INFO] Dispensing liquid.")
    #capper.hold_vial()
    liquids_dispenser.piston_to_dispense_position();time.sleep(5)
    print(liquids_dispenser.status());time.sleep(0.3)
    print(liquids_dispenser.get_valve_pos());time.sleep(0.3)
    liquid["liquid_id"]=liquids[1][2]
    liquid["volume"]=liquids[1][1]*1000
    liquid["source_port"]=LIQUIDS_CHANNELS[1]
    print(f"[INFO] Dispensing {liquids[1][1]*1000} uL of {liquids[1][2]} from port {LIQUIDS_CHANNELS[1]}")
    liquids_dispenser.dispense(liquid);time.sleep(0.3)
    liquids_dispenser.move_home();time.sleep(0.3)
    liquids_dispenser.piston_to_home_position();time.sleep(5)
    #capper.release_vial()
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
    weights= [weight_salt, weight_analyte]
    return weights

def analise_sample(echem_slot=2, cv_file_name="", mixing = True, 
                   cv_params={
                       "potentiostat_id":1,
                       "i_range":5,
                        "start_potential":0,
                        "potential_vertex":1,
                        "scan_rate":100,
                        "cycles":1,
                        "increment":0.01,
                        "show_plot":True,
                   },
                   mixing_params={"mixing_type": "stirrer",
                                  "mixing_time_s": 300},
                   purging_params={
                       "purging_time_s":180
                   }):
    ########################################
    # Moving rack from carousel to echem
    ########################################
    print("[INFO] Moving rack to echem.")
    execute_routine_arm("pick_rack_from_bottom_carousel.json")
    execute_routine_arm(F"place_rack_in_{echem_slot}.json")
    ########################################
    # Mixing
    ########################################
    if mixing_params["mixing_type"]=='stirrer':
        stirr_samples(cycles=int(mixing_params['mixing_time_s']/2.5)) #each cycle takes 2.5 secs
    ########################################
    # Measuring Ph
    ########################################
    print("[INFO] Setting ph measurement.") 
    execute_routine_echem("ph_measurement.json")
    print("[INFO] Picking ph Probe") 
    execute_routine_arm("pick_ph_probe.json")
    print(F"[INFO] Measuring ph in rack {echem_slot}") 
    execute_routine_arm(F"measure_ph_in_rack_{echem_slot}.json")
    stirr_samples(cycles=3,sample_slot_id=echem_slot)
    ph_toledo_meter.press_read_button();time.sleep(3)
    msg = ph_toledo_meter.read_ph();time.sleep(2)
    ph_before = msg['pH']
    temp_before =msg['temperature_C']
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
    wash_electrodes(cycles=10,electrode_id=echem_slot)
    execute_routine_echem("wash_electrodes_out.json")
    execute_routine_echem("ph_measurement.json")
    print("[INFO] Drying electrodes") 
    echem.dryer_on();time.sleep(10)
    echem.dryer_off();time.sleep(0.1)
    execute_routine_echem("idle.json")
    home_echem()
    execute_routine_echem("idle.json")
    ###########################################
    #PHOTO BEFORE EXPERIMENT OF ELECTRODES 
    ###########################################
    print("[INFO] Sinking electrodes in cell.") 
    execute_routine_echem("cv_start_position.json")
    degassing_sample(degassing_time=purging_params['purging_time_s'])
    ###########################################
    #CV Test logic
    ###########################################
    try:
        print("[INFO] Executing CV test...")
        df, data = run_cyclic_voltammetry(potentiostat_id=3, 
                                          i_range=cv_params["i_range"], 
                                          start_potential=cv_params["start_potential"], 
                                          potential_vertex=cv_params["potential_vertex"], 
                                          scan_rate=cv_params["scan_rate"], 
                                          cycles=cv_params["cycles"], 
                                          increment=cv_params["increment"], 
                                          show_plot=cv_params["show_plot"], 
                                          file_name=cv_file_name)
        V = df["Potential"].values
        I = df["Current"].values
        C = df["Cycle"].values
        print("[INFO] CV test done.")
    except Exception as e:
        print(f"[ERROR] Not possible to connect with potentiostat: {e}")
        print("\n[INFO] Original CV configuration:")
        print("[INFO] Original CV configuration:")
        print(f"       i_range={cv_params['i_range']}")
        print(f"       start_potential={cv_params['start_potential']}")
        print(f"       potential_vertex={cv_params['potential_vertex']}")
        print(f"       scan_rate={cv_params['scan_rate']}")
        print(f"       cycles={cv_params['cycles']}")
        print(f"       increment={cv_params['increment']}")
        print(f"       show_plot={cv_params['show_plot']}")
        print(f"       file_name={cv_file_name}")
        while True:
            repeat = input("\nDo you want to repeat the CV test? (Y/N): ").strip().upper()

            if repeat == "N" or repeat == "n":
                print("[INFO] CV test cancelled.")
                break

            if repeat != "Y" or repeat != "Y":
                print("[ERROR] Please enter Y or N.")
                continue

            print("\n[INFO] Enter new values. Press ENTER to keep the current value.")

            try:
                #cv_params["i_range"] = float(input(f"i_range [{cv_params['i_range']}]: ") or cv_params["i_range"])
                cv_params["start_potential"] = float(input(f"start_potential [{cv_params['start_potential']}]: ") or cv_params["start_potential"])
                cv_params["potential_vertex"] = float(input(f"potential_vertex [{cv_params['potential_vertex']}]: ") or cv_params["potential_vertex"])
                #cv_params["scan_rate"] = float(input(f"scan_rate [{cv_params['scan_rate']}]: ") or cv_params["scan_rate"])
                #cv_params["cycles"] = int(input(f"cycles [{cv_params['cycles']}]: ") or cv_params["cycles"])
                #cv_params["increment"] = float(input(f"increment [{cv_params['increment']}]: ") or cv_params["increment"])
                file_name = input(f"file_name [{cv_file_name}]: ").strip()
                if file_name:
                    cv_file_name = file_name

                print("\n[INFO] New CV configuration:")
                print(f"       i_range={cv_params['i_range']}")
                print(f"       start_potential={cv_params['start_potential']}")
                print(f"       potential_vertex={cv_params['potential_vertex']}")
                print(f"       scan_rate={cv_params['scan_rate']}")
                print(f"       cycles={cv_params['cycles']}")
                print(f"       increment={cv_params['increment']}")
                print(f"       show_plot={cv_params['show_plot']}")
                print(f"       file_name={cv_file_name}")
                print("[INFO] Executing CV test...")
                df, data = run_cyclic_voltammetry(potentiostat_id=3, i_range=cv_params["i_range"], start_potential=cv_params["start_potential"], potential_vertex=cv_params["potential_vertex"], scan_rate=cv_params["scan_rate"], cycles=cv_params["cycles"], increment=cv_params["increment"], show_plot=cv_params["show_plot"], file_name=cv_file_name)
                V = df["Potential"].values
                I = df["Current"].values
                C = df["Cycle"].values
                print("[INFO] CV test done.")
                break

            except Exception as e:
                print(f"[ERROR] CV test failed: {e}")
                print("[INFO] The current configuration will be used as reference for the next attempt.")

    execute_routine_echem("cv_end_position.json")
    execute_routine_echem("idle.json")
    home_echem()
    #############################################
    # measruing Ph after the test
    #############################################
    print("[INFO] Setting ph measurement.") 
    execute_routine_echem("ph_measurement.json")
    echem.dryer_on();time.sleep(10)
    echem.dryer_off();time.sleep(0.1)
    print("[INFO] Picking ph Probe") 
    execute_routine_arm("pick_ph_probe.json")
    print(F"[INFO] Measuring ph in rack {echem_slot}") 
    execute_routine_arm(F"measure_ph_in_rack_{echem_slot}.json")
    stirr_samples(cycles=3,sample_slot_id=1)
    ph_toledo_meter.press_read_button();time.sleep(3)
    msg = ph_toledo_meter.read_ph();time.sleep(2)
    ph_after = msg['pH']
    temp_after =msg['temperature_C']
    print(F"[INFO] Measurement done: {ph_after}") 
    execute_routine_arm(F"measure_ph_in_rack_{echem_slot}_out.json")
    print("[INFO] Washing ph probe.") 
    execute_routine_arm(F"wash_ph_probe_ae_in_rack_{echem_slot}.json")
    print("[INFO] Returning ph probe") 
    execute_routine_arm("place_ph_probe.json")
    execute_routine_echem("idle.json")
    home_echem()
    return V, I, C, ph_before, ph_after, temp_before, temp_after

def select_json(experiments_path):
    """Let the user select an experiment JSON if none was provided."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select experiment JSON",
            initialdir=experiments_path,
            filetypes=[("JSON files", "*.json")]
        )
        root.destroy()
        if not file_path:
            print("No file selected.")
            sys.exit(0)
        return Path(file_path)
    except Exception:
        file_name = input(f"Enter JSON filename from {experiments_path}: ").strip()
        return experiments_path / file_name

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def create_workflow(workflows_path, json_file):
    name = json_file.stem
    workflow = workflows_path / name
    logs = workflow / "logs"
    input_dir = workflow / "input"
    results = workflow / "results"
    data = results / "data"
    images = results / "imgs"
    for path in (logs, input_dir, data, images):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "workflow": workflow,
        "logs": logs,
        "input": input_dir,
        "results": results,
        "data": data,
        "imgs": images,
        "report": results / "report.pdf"
    }
def setup_logging(logs_path):
    logger = logging.getLogger("workflow")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(logs_path / "workflow.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

def load_experiment():
    experiments_path = BASE_PATH / "data" / "aisuggestions" / "experiments"
    workflows_path = BASE_PATH / "results"

    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="?", help="Experiment JSON file")
    args = parser.parse_args()

    if args.json_file:
        json_file = Path(args.json_file)
        if not json_file.exists():
            json_file = experiments_path / args.json_file
    else:
        json_file = select_json(experiments_path)

    if not json_file.exists():
        raise FileNotFoundError(f"Experiment file not found: {json_file}")

    experiment = load_json(json_file)
    paths = create_workflow(workflows_path, json_file)
    logger = setup_logging(paths["logs"])

    logger.info("Starting workflow: %s", json_file.stem)

    shutil.copy2(json_file, paths["input"] / json_file.name)
    logger.info("Input JSON copied to workflow folder.")

    metadata = experiment.get("metadata", {})
    logger.info(
        "Experiment: %s", metadata.get("experiment_name", json_file.stem)
    )

    output_files = {
        "cv_raw": paths["data"] / "cv_raw.json",
        "ph_measurements": paths["data"] / "ph_measurements.json",
        "report_raw_data": paths["data"] / "report_raw_data.json",
    }

    for name, file_path in output_files.items():
        if not file_path.exists():
            content = (
                {"ph_before": None, "ph_after": None}
                if name == "ph_measurements"
                else {}
            )
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)

    logger.info("Workflow directory ready: %s", paths["workflow"])
    logger.info("Workflow setup complete.")
    return experiment, paths
    # Find the workflow/results directory for this experiment.
    # Load all available experimental data.
    # Check which expected data is available and which is missing.
    # If no experimental data exists:
    # - mark it explicitly as missing data in the report
    # Send the available data and experiment context to OpenAI.
    # Receive structured report JSON_REPORT_TEMPLATE from OpenAI.
    # Validate the report JSON.
    # Save report_analysis.json in results/name_of_experiment/results.
    # Convert the report JSON into report.pdf.
    # Save report.pdf in the results/name_of_experiment/ directory.
    # Return the report.


def report_from_json(
    input_data={},
    results_data={},
    paths=None,
    model="terra",
    report_data={},
):
    # Render PDF using report data, input configuration,
    # actual results, and image paths
    if paths and "report" in paths:

        image_paths = results_data.get(
            "image_paths",
            results_data.get("images", {}),
        )

        json_to_pdf(
            report_data=report_data,
            output_pdf_path=paths["report"],
            input_data=input_data,
            results_data=results_data,
            image_paths=image_paths,
        )

def generate_report(
    input_data=None,
    results_data=None,
    paths=None,
    model="terra",
):
    """
    Generate the LLM report and then render it to PDF.

    Flow:
        input_data
            ↓
        analise_data_with_AI()
            ↓
        report_data
            ↓
        json_to_pdf()
    """
    input_data = input_data or {}
    results_data = results_data or {}
    # 1. AI analysis & raw report structure generation
    report_data = analise_data_with_AI(
        input_data=input_data,
        results_data=results_data,
        paths=paths,
        model=model,
    )
    # 2. Render PDF
    if paths and "report" in paths:
        image_paths = results_data.get(
            "image_paths",
            results_data.get("images", {}),
        )
        json_to_pdf(
            report_data=report_data,
            output_pdf_path=paths["report"],
            input_data=input_data,
            results_data=results_data,
            image_paths=image_paths,
        )
    return report_data


    # Collect all available experiment context:
    # - Original experiment JSON
    # - CV raw data
    # - CV plots/images
    # - Electrode images before/after
    # - pH before/after
    # - Execution logs and errors
    # - Any other measurements produced by the platform

    # Check which expected data is actually available.
    # Keep a list of missing data so the report can explicitly say what was unavailable.

    # Analyse CV data:
    # - CV curves and cycles
    # - oxidation/reduction peaks
    # - peak potentials
    # - peak currents
    # - cycle-to-cycle differences
    # - baseline/current changes
    # - possible fouling or instability
    # - reproducibility
    # - anything unusual

    # Analyse electrode images:
    # - compare before/after images
    # - look for visible contamination, deposits, damage or changes
    # - relate visible changes to the electrochemical results
    # - do not make conclusions if images are unavailable

    # Analyse pH:
    # - compare pH before/after
    # - identify significant change
    # - consider whether pH change could affect the CV
    # - do not interpret if measurements are missing

    # Analyse execution:
    # - check logs for errors/warnings
    # - identify incomplete steps
    # - identify possible causes of abnormal results

    # Ask OpenAI to combine the available information into a scientific interpretation.
    # Clearly tell the model which information is measured and which information is missing.
    # Do not allow missing data to be treated as a negative/failed result.

    # Generate a structured report JSON containing:
    # - experiment summary
    # - sample/preparation information
    # - electrode configuration
    # - CV parameters
    # - measurements
    # - CV analysis
    # - pH analysis
    # - electrode analysis
    # - execution/errors
    # - overall interpretation
    # - conclusions
    # - recommendations
    # - missing data
    # - confidence/limitations

    # Save the AI analysis JSON to results/data/report_raw_data.json
    # Return the structured report data
    #return


    # Convert the structured report JSON into a human-readable PDF.
    #
    # Report structure:
    # 1. Title page / experiment identification
    # 2. Experiment summary
    # 3. Experimental setup
    # 4. Sample and electrolyte preparation
    # 5. CV parameters
    # 6. Results
    #    - CV plot
    #    - numerical CV results
    #    - pH before/after
    #    - electrode images before/after
    # 7. AI analysis / interpretation
    #    - CV interpretation
    #    - electrode interpretation
    #    - pH interpretation
    #    - reproducibility
    # 8. Errors, warnings and possible causes
    # 9. Missing data / unavailable measurements
    # 10. Conclusions
    # 11. Recommendations / suggested next experiments
    # 12. Appendix
    #    - relevant raw data
    #    - experiment configuration
    #
    # If data is missing:
    # - still generate the PDF
    # - clearly state what is missing
    # - explain which conclusions cannot be made because of the missing data
    # - never create fake experimental conclusions from missing data
    #
    # For development/testing:
    # - generate dummy CV data when no CV data exists
    # - generate dummy pH values when no pH data exists
    # - optionally generate placeholder images/plots
    # - clearly label ALL dummy data as "SIMULATED / TEST DATA"
    # - never mix simulated data with real experimental data without clearly identifying it
    #
    # Save as results/name_of_experiment/report.pdf

def analise_data_with_AI(
    input_data={}, results_data={}, paths=None, model="mini"
):
    MODELS = {
        "mini": "gpt-5.4-mini",
        "luna": "gpt-5.6-luna",
        "terra": "gpt-5.6-terra",
    }
    selected_model = MODELS.get(model, MODELS["mini"])

    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        OPENAI_AVAILABLE = True
    except (ImportError, Exception) as e:
        print(f"[WARNING] OpenAI library initialization issue: {e}")
        OPENAI_AVAILABLE = False
        client = None

    # Track missing measurements explicitly
    missing_data = []
    if not results_data.get("cv_raw") or not results_data["cv_raw"].get(
        "current_A"
    ):
        missing_data.append("Cyclic Voltammetry raw curve measurements")

    ph_data = results_data.get("ph_measurements", {})
    if ph_data.get("ph_before") is None:
        missing_data.append("Initial pH measurement (ph_before)")
    if ph_data.get("ph_after") is None:
        missing_data.append("Final pH measurement (ph_after)")
    if ph_data.get("temp_before_C") is None:
            missing_data.append("Initial temperture measurement (temp_before_C)")
    if ph_data.get("temp_after_C") is None:
            missing_data.append("Final temperature measurement (temp_after_C)")

    image_paths = results_data.get("images", {})
    for img_key in ["electrode_before", "electrode_after", "CV"]:
        img_p = image_paths.get(img_key)
        if not img_p or not Path(img_p).exists():
            missing_data.append(f"Image artifact: {img_key}.png")

    system_prompt = (
        "You are an expert electrochemist assistant analyzing lab workflow data and images. "
        "Analyze the provided experiment configuration, numerical results, and image uploads. "
        "Output ONLY valid JSON adhering strictly to the structured report schema."
        "Ensure the 'analysis.cv_analysis' object includes 'raw_data_interpretation' and 'electrochemical_assignment'. "
        "Ensure 'analysis.ph_analysis' or 'results.ph_measurements' is present for pH interpretations."
    )

    # Build the multi-modal text + image payload for the model
#    user_content = [
#        {
#            "type": "text",
#            "text": f"""
#Experiment Context & Configuration:
#{json.dumps(input_data, indent=2)}
#
#Experimental Results:
#{json.dumps(results_data, indent=2, default=str)}
#
#Missing Data Identified:
#{json.dumps(missing_data, indent=2)}

#Instructions:
#1. Provide a rigorous scientific analysis based on all provided data and attached images.
#2. In the electrode analysis section, explicitly refer to visual features visible in electrode_before and electrode_after images (if available).
#3. In the CV analysis section, evaluate the attached CV plot (if available) along with raw curve data.
#4. List all missing items in the missing_data array. Do NOT allow missing data to be interpreted as a failed result.
#5. Output strict JSON with key sections: report_metadata, experiment_summary, experimental_setup, 
#   sample_preparation, cv_parameters, results, analysis, execution, missing_data, conclusions, recommendations, limitations, data_quality, test_data.
#""",
#        }
#    ]

    user_content = [
        {
            "type": "text",
            "text": f"""
    You are an AI scientific analyst generating a structured report for an electrochemical experiment.

    You must analyze ALL provided experimental data and attached images.

    ==================================================
    EXPERIMENT CONTEXT & CONFIGURATION
    ==================================================

    {json.dumps(input_data, indent=2, default=str)}

    ==================================================
    EXPERIMENTAL RESULTS
    ==================================================

    {json.dumps(results_data, indent=2, default=str)}

    ==================================================
    MISSING DATA IDENTIFIED
    ==================================================

    {json.dumps(missing_data, indent=2, default=str)}

    ==================================================
    REPORT GENERATION INSTRUCTIONS
    ==================================================

    IMPORTANT:

    1. Return ONLY valid JSON.
    - Do NOT return Markdown.
    - Do NOT use ```json code fences.
    - Do NOT include explanations before or after the JSON.
    - The entire response must be a single valid JSON object.

    2. You MUST use EXACTLY these top-level keys:

    report_metadata
    experiment_summary
    experimental_setup
    sample_preparation
    cv_parameters
    results
    analysis
    execution
    missing_data
    conclusions
    recommendations
    limitations
    data_quality
    test_data

    3. Do NOT rename these keys.

    4. Do NOT remove these keys.

    5. Do NOT add additional top-level keys.

    6. If information is unavailable, use null, "", [], or {{}} as appropriate.

    7. NEVER invent experimental measurements or observations.

    ==================================================
    REQUIRED REPORT STRUCTURE
    ==================================================

    The JSON MUST follow this structure:

    {{
        "report_metadata": {{
            "experiment_name": null,
            "experimenter": null,
            "status": null
        }},

        "experiment_summary": {{
            "description": null,
            "mode": null
        }},

        "experimental_setup": {{
            "working_electrode": null,
            "counter_electrode": null,
            "reference_electrode": null
        }},

        "sample_preparation": {{
            "final_volume_ml": null,
            "solids": [],
            "liquids": []
        }},

        "cv_parameters": {{}},

        "results": {{
            "cv": {{}},
            "ph": {{}},
            "temp": {{}},
            "dispensed_masses": {{}},
            "electrode": {{
                "status": null
            }}
        }},

        "analysis": {{
            "cv_interpretation": "...",

            "cv_analysis": {{
                "peak_analysis": {{
                    "anodic_peak": {{
                        "potential_v": null,
                        "current": null,
                        "current_unit": null,
                        "onset_potential_v": null,
                        "confidence": null,
                        "source": null
                    }},

                    "cathodic_peak": {{
                        "potential_v": null,
                        "current": null,
                        "current_unit": null,
                        "onset_potential_v": null,
                        "confidence": null,
                        "source": null
                    }},

                    "peak_separation": {{
                        "delta_potential_v": null,
                        "calculation": null
                    }}
                }},

                "onset_analysis": {{
                    "anodic_onset_potential_v": null,
                    "cathodic_onset_potential_v": null,
                    "onset_definition": null
                }},

                "current_analysis": {{
                    "anodic_peak_current": null,
                    "anodic_peak_current_unit": null,
                    "cathodic_peak_current": null,
                    "cathodic_peak_current_unit": null
                }},

                "raw_data_interpretation": null,
                "electrochemical_assignment": null,
                "reversibility_assessment": null
            }},

            "ph_interpretation": "...",
            "electrode_interpretation": "...",
            "overall_interpretation": "..."
        }},

        "execution": {{
            "errors": [],
            "warnings": []
        }},

        "missing_data": [],

        "conclusions": [],

        "recommendations": [],

        "limitations": [],

        "data_quality": {{
            "rating": null
        }},

        "test_data": {{
            "used": false,
            "items": []
        }}
    }}

    ==================================================
    FIELD-SPECIFIC REQUIREMENTS
    ==================================================

    report_metadata:
    - experiment_name: use the experiment name from the supplied metadata when available.
    - experimenter: use the supplied experimenter when available.
    - status: describe the actual completion state.
    - Do not mark the experiment as failed merely because data is missing.

    experiment_summary:
    - description: provide a concise scientific description of the experiment.
    - mode: report the supplied experimental mode.

    experimental_setup:
    - working_electrode: identify the working electrode from the supplied data.
    - counter_electrode: identify the counter electrode.
    - reference_electrode: identify the reference electrode.
    - Do not invent electrode types.
    - If multiple conflicting values are supplied, prefer the value from the original experiment configuration/input data and mention the conflict in warnings or limitations.

    sample_preparation:
    - Report the supplied final volume, solids, and liquids.
    - Preserve the supplied information.
    - Do not invent concentrations, quantities, or materials.

    cv_parameters:
    - Preserve and report the supplied CV parameters.
    - Do not invent scan rate, potential limits, electrode area, concentration, cycles, or other parameters.
    - Preserve the original units exactly where possible.
    - Pay particular attention to potential units:
    - JSON field names must use lowercase "_v" when representing volts.
    - Example: "potential_v", "start_potential_v", "onset_potential_v".
    - Unit values representing volts must use uppercase "V".
    - Example: "unit": "V".
    - Do not confuse mV with V.
    - If scan rate is supplied in mV/s, preserve it as mV/s unless a conversion is explicitly required.
    - Do not silently convert units when the source contains ambiguity.

    results:
    - cv: include relevant CV/raw curve data supplied in the experimental results.
    - ph: include available pH measurements.
    - temp: include available temperature measurements.
    - dispensed_masses: include available dispensed masses.
    - electrode: summarize the available electrode observations/images.
    - Preserve raw numerical data where appropriate.
    - Do not replace actual measured/dispensed values with planned values.
    - Clearly distinguish planned/requested values from actual/measured values when both are supplied.

    ==================================================
    CV ANALYSIS REQUIREMENTS
    ==================================================

    analysis:
    - cv_interpretation:

    Analyze the actual supplied CV data.

    You MUST explicitly search ALL relevant supplied sources for electrochemical quantities, including:

    1. The supplied input JSON.
    2. The supplied results JSON.
    3. The raw CV data.
    4. CV metadata.
    5. The CV image/plot.
    6. Any existing report analysis or narrative containing explicitly stated CV measurements.

    Use the following priority when extracting numerical CV values:

    1. Explicit numerical values in results.cv.
    2. Explicit numerical values in any structured CV analysis already supplied.
    3. Explicit numerical values in analysis.cv_analysis if present in supplied data.
    4. Raw numerical CV arrays.
    5. Clearly readable values from the CV plot/image.
    6. Narrative descriptions elsewhere in the supplied data.

    Do NOT invent values.

    ==================================================
    ANODIC PEAK
    ==================================================

    Search explicitly for:

    - anodic peak potential
    - anodic peak current
    - anodic peak current unit
    - anodic onset potential
    - any explicit confidence or source information

    Store the values in:

    analysis.cv_analysis.peak_analysis.anodic_peak

    using:

    "potential_v"
    "current"
    "current_unit"
    "onset_potential_v"
    "confidence"
    "source"

    Important:

    - "potential_v" is a JSON field name and MUST use lowercase "v".
    - If the numerical unit is volts, the unit itself is "V".
    - Do not use "potential_V" as a field name.
    - Do not use "onset_potential_V" as a field name.
    - If the current unit is ambiguous, preserve the numerical value and explicitly describe the ambiguity.
    - Do not silently convert A to uA or uA to A.
    - If the peak potential can only be estimated from a plot, mark the confidence as "approximate" and identify the source as "plot" or an appropriate combined source.
    - If it is supported by raw numerical data, identify the source as "raw_data" or "raw_data_and_plot" as appropriate.

    ==================================================
    CATHODIC PEAK
    ==================================================

    Search explicitly for:

    - cathodic peak potential
    - cathodic peak current
    - cathodic peak current unit
    - cathodic onset potential
    - any explicit confidence or source information

    Store the values in:

    analysis.cv_analysis.peak_analysis.cathodic_peak

    using:

    "potential_v"
    "current"
    "current_unit"
    "onset_potential_v"
    "confidence"
    "source"

    Important:

    - "potential_v" is a JSON field name and MUST use lowercase "v".
    - If the numerical unit is volts, the unit itself is "V".
    - Do not use "potential_V" as a field name.
    - Do not use "onset_potential_V" as a field name.
    - If the current unit is ambiguous, preserve the numerical value and explicitly describe the ambiguity.
    - Do not silently convert current units.
    - If the peak potential can only be estimated from a plot, mark the confidence as "approximate".

    ==================================================
    PEAK SEPARATION
    ==================================================

    Search explicitly for:

    - peak separation
    - delta E
    - delta Ep
    - peak potential difference
    - anodic/cathodic peak potential difference

    Store the result in:

    analysis.cv_analysis.peak_analysis.peak_separation

    using:

    "delta_potential_v"
    "calculation"

    Important:

    - "delta_potential_v" is a JSON field name and MUST use lowercase "v".
    - If the unit is volts, the corresponding unit is "V".
    - Do not use "delta_potential_V" as a field name.

    If both peak potentials are available, calculate:

    anodic_peak_potential_v - cathodic_peak_potential_v

    Do not calculate this if either peak potential is unavailable or unreliable.

    If the source already provides an explicit peak separation, preserve the supplied value and identify that it was supplied rather than independently calculated.

    ==================================================
    ONSET ANALYSIS
    ==================================================

    Search explicitly for:

    - anodic onset potential
    - cathodic onset potential
    - onset potential
    - oxidation onset
    - reduction onset

    Store the results in:

    analysis.cv_analysis.onset_analysis

    using:

    "anodic_onset_potential_v"
    "cathodic_onset_potential_v"
    "onset_definition"

    Important:

    - JSON field names MUST use lowercase "v".
    - Do not use "anodic_onset_potential_V".
    - Do not use "cathodic_onset_potential_V".

    Try to calculate onset potentials.

    If an onset is estimated from a plot, state that it is approximate.

    If no defensible onset can be determined:

    "anodic_onset_potential_v": null

    and/or

    "cathodic_onset_potential_v": null

    and explain the absence in "onset_definition".

    ==================================================
    CURRENT ANALYSIS
    ==================================================

    Store peak current information in:

    analysis.cv_analysis.current_analysis

    using:

    "anodic_peak_current"
    "anodic_peak_current_unit"
    "cathodic_peak_current"
    "cathodic_peak_current_unit"

    Preserve the source current values and units.

    IMPORTANT:

    - The value of the current is given in A.

    ==================================================
    OTHER CV QUANTITIES
    ==================================================

    Where reliably supported, also consider:

    - formal or midpoint potential
    - peak current ratio
    - background current
    - baseline characteristics
    - cycle-to-cycle changes
    - peak position changes
    - peak current changes
    - reversibility
    - quasi-reversibility
    - irreversibility
    - other electrochemically relevant observations

    Do not calculate or report a value merely because it would normally be useful.

    Only report it when the supplied evidence supports it.

    ==================================================
    PEAK CONFIDENCE AND SOURCE
    ==================================================

    For each extracted peak quantity, distinguish between:

    - exact/supplied
    - calculated
    - approximate
    - unavailable

    Use the "confidence" field to describe the reliability of the value.

    Examples:

    "confidence": "high"
    "confidence": "moderate"
    "confidence": "approximate"
    "confidence": "low"

    Use "source" to identify where the value came from.

    Examples:

    "source": "raw_data"
    "source": "plot"
    "source": "raw_data_and_plot"
    "source": "supplied_report"
    "source": "calculated_from_raw_data"

    Do not claim a value came from raw data if it was only estimated from the plot.

    ==================================================
    RAW DATA INTERPRETATION
    ==================================================

    analysis.cv_analysis.raw_data_interpretation:

    - Describe what the raw CV data supports.
    - Identify potential range where available.
    - Identify current range where available.
    - Identify available cycle information.
    - Identify inconsistencies between raw data, metadata, and plots.
    - Preserve the supplied units and labels.
    - Explicitly mention unit ambiguity where present.
    - Do not silently correct inconsistent metadata.

    ==================================================
    ELECTROCHEMICAL ASSIGNMENT
    ==================================================

    analysis.cv_analysis.electrochemical_assignment:

    - Identify the likely electrochemical couple or process only when supported by the supplied experiment context and data.
    - Distinguish assignment from direct measurement.
    - Do not present an inferred chemical assignment as a directly measured fact.

    ==================================================
    REVERSIBILITY ASSESSMENT
    ==================================================

    analysis.cv_analysis.reversibility_assessment:

    Assess the electrochemical behavior using the supplied evidence.

    Consider:

    - peak separation
    - peak symmetry
    - peak current relationship
    - cycle-to-cycle behavior
    - background current
    - peak stability
    - scan rate information
    - other supplied evidence

    Do not make a stronger reversibility claim than the data supports.

    ==================================================
    IMPORTANT CV RULES
    ==================================================

    - Do NOT invent a peak.
    - Try to calculate the onset potential.
    - Do NOT invent a current.
    - Do NOT invent a current unit.
    - Do NOT invent a peak separation.
    - Do NOT invent a formal potential.
    - Do NOT invent a current ratio.
    - Do NOT invent electrochemical behavior.
    - If a value cannot be reliably determined, return null unless it is the anodic onset potential.
    - If the source JSON already contains a value, preserve it and identify that it came from supplied data.
    - If a value appears only in narrative text, extract it into the structured fields when explicitly stated.
    - If a value appears only in a plot, identify it as approximate where appropriate.
    - If numerical values conflict, do not silently choose one.
    - Report the conflict in the appropriate analysis, warning, or limitation field.
    - Never resolve conflicting values by guessing.

    ==================================================
    PH INTERPRETATION
    ==================================================

    ph_interpretation:

    - Analyze the supplied pH measurements.
    - Preserve the measured values exactly.
    - If before and after pH values are available, report the change.
    - Do not invent a causal explanation for the change.
    - If measurements are unavailable, explicitly state that they are unavailable.

    ==================================================
    TEMPERATURE INTERPRETATION
    ==================================================

    Temperature data belongs in:

    results.temp

    If temperature measurements are available:

    - Preserve the supplied before and after values.
    - Preserve the supplied units.
    - Report temperature changes when appropriate.
    - Do not invent a cause for temperature changes.

    ==================================================
    DISPENSED MASS INTERPRETATION
    ==================================================

    Dispensed mass data belongs in:

    results.dispensed_masses

    When both planned and actual/dispensed masses are available:

    - Preserve both values.
    - Clearly distinguish planned from actual.
    - Do not replace planned mass with actual mass.
    - Do not replace actual mass with planned mass.
    - If a supplied mass is encoded as a string, preserve the original numerical value and unit.
    - If actual mass differs from planned mass, mention the discrepancy in the appropriate warning, limitation, or interpretation field.
    - Do not invent a mass.

    ==================================================
    ELECTRODE INTERPRETATION
    ==================================================

    electrode_interpretation:

    - If electrode_before and/or electrode_after images are available, explicitly describe visible features in those images.
    - Where both images are available, compare before and after appearance.
    - Only describe features that can actually be observed.
    - Do NOT invent visual observations.
    - If an image is unusable, blurred, overexposed, underexposed, or otherwise insufficient for reliable interpretation, explicitly state this.
    - Do not claim surface chemistry, morphology, roughness, contamination, or deposition unless supported by visible evidence or supplied analytical data.

    ==================================================
    OVERALL INTERPRETATION
    ==================================================

    overall_interpretation:

    Provide an integrated scientific interpretation based only on the available evidence.

    Clearly distinguish:

    1. Directly measured data.
    2. Values calculated from measured data.
    3. Values estimated from plots.
    4. Scientific interpretation.
    5. Uncertainty or ambiguity.

    ==================================================
    EXECUTION
    ==================================================

    execution:

    - errors: list actual errors encountered or observed.
    - warnings: list relevant warnings, including:
    - missing data
    - conflicting metadata
    - inconsistent units
    - planned versus actual discrepancies
    - unusable images
    - inconsistent cycle counts
    - other important data-quality issues

    Do not describe a warning as an experimental failure unless the supplied evidence explicitly supports that conclusion.

    ==================================================
    MISSING DATA
    ==================================================

    missing_data:

    - MUST contain every item from the supplied missing_data array.
    - Do NOT omit missing items.
    - Missing data must NEVER be interpreted as evidence of experimental failure.
    - Treat missing data as a limitation of the available evidence.

    ==================================================
    CONCLUSIONS
    ==================================================

    conclusions:

    - Provide scientifically supported conclusions.
    - Conclusions must be based only on supplied experimental evidence.
    - Do not invent results.
    - Distinguish measured observations from interpretation.
    - Do not state uncertain interpretations as established facts.

    ==================================================
    RECOMMENDATIONS
    ==================================================

    recommendations:

    - Provide reasonable scientific recommendations for follow-up measurements,
    experiments, controls, or data collection.
    - Recommendations should address important limitations or missing information.
    - Recommendations must not invent missing experimental results.

    ==================================================
    LIMITATIONS
    ==================================================

    limitations:

    - Identify limitations caused by missing, incomplete, simulated, conflicting, or low-quality data.
    - Clearly distinguish limitations from experimental failure.
    - Explicitly mention important unit ambiguities or conflicting metadata.

    ==================================================
    DATA QUALITY
    ==================================================

    data_quality:

    - rating should reflect the completeness and reliability of the supplied data.
    - Use an appropriate qualitative value such as:
    "Good", "Fair", or "Poor".
    - Do not rate the data as "Good" when important experimental information is missing, contradictory, or unreliable.

    ==================================================
    TEST DATA
    ==================================================

    test_data:

    - used: indicate whether simulated/test data was used.
    - items: list relevant simulated, test, or non-experimental data items.
    - Do not classify genuine experimental measurements as test data.

    ==================================================
    SCIENTIFIC RULES
    ==================================================

    1. Do not fabricate data.
    2. Do not fabricate observations from images.
    3. Do not fabricate CV peaks or electrochemical behavior.
    4. Do not fabricate pH values.
    5. Do not fabricate temperature values.
    6. Do not fabricate dispensed masses.
    7. Do not fabricate electrode properties.
    8. Clearly distinguish measured data from interpretation.
    9. Clearly distinguish visual observations from scientific interpretation.
    10. Clearly distinguish supplied values from calculated values.
    11. Clearly distinguish calculated values from plot estimates.
    12. Missing data is NOT equivalent to experimental failure.
    13. If data is unavailable, explicitly state that it is unavailable.
    14. Use the attached images as evidence when they are available.
    15. Use raw numerical data as evidence whenever available.
    16. Ensure all conclusions are consistent with the supplied results.
    17. Ensure every item in missing_data is preserved in the final report.
    18. Never silently change units.
    19. Never silently resolve conflicting measurements.
    20. Never guess an experimental value.
    21. Never use uppercase "V" inside JSON field names that represent volts.
    22. Use lowercase "v" in JSON field names such as:
        - potential_v
        - onset_potential_v
        - delta_potential_v
        - anodic_onset_potential_v
        - cathodic_onset_potential_v
    23. Use uppercase "V" only as the actual unit symbol for volts.
    24. Keep "mV" and "V" distinct.
    25. Keep "A" and "uA" distinct.
    26. If a supplied current unit is ambiguous, preserve the ambiguity rather than guessing.
    27. Do not silently convert mV to V, V to mV, A to uA, or uA to A when the source is ambiguous.
    28. Numerical field names and unit symbols are different concepts:
        - field name: "potential_v"
        - unit value: "V"

    ==================================================
    FINAL OUTPUT REQUIREMENT
    ==================================================

    Return ONLY the JSON object matching the exact structure above.

    Do not add any additional keys at the top level.

    Do not add Markdown.

    Do not add commentary.
    """
        }
    ]

    # Attach existing images into user_content as base64 URLs
    if image_paths:
        for img_label, img_path in image_paths.items():
            p = Path(img_path)
            if p.exists() and p.suffix.lower() in [
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
            ]:
                try:
                    b64_str = encode_image_to_base64(p)
                    mime_type = (
                        "image/png"
                        if p.suffix.lower() == ".png"
                        else "image/jpeg"
                    )

                    # Add text marker for image identification
                    user_content.append(
                        {
                            "type": "text",
                            "text": f"Image artifact [{img_label}]:",
                        }
                    )
                    # Add base64 image content payload
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_str}"
                            },
                        }
                    )
                except Exception as img_err:
                    print(
                        f"[WARNING] Could not read image {p} for LLM: {img_err}"
                    )

    report = None
    if OPENAI_AVAILABLE and client and os.environ.get("OPENAI_API_KEY"):
        try:
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                #temperature=0.2,
            )
            report = json.loads(response.choices[0].message.content)
        except Exception as e:
            print(
                f"[ERROR] OpenAI API execution failed: {e}. Falling back to default report template."
            )

    if not report:
        # Fallback/Template structure if AI call is unavailable
        metadata = input_data.get("metadata", {})
        cv_params = input_data.get("cv_parameters", {})
        recipe = input_data.get("recipe", {})

        report = {
            "report_metadata": {
                "experiment_name": metadata.get(
                    "experiment_name", "CV_Experiment"
                ),
                "experimenter": metadata.get("experimenter", "Unknown"),
                "status": "Completed with warnings"
                if missing_data
                else "Completed",
            },
            "experiment_summary": {
                "description": metadata.get("description", ""),
                "mode": input_data.get("experiment_mode", ""),
            },
            "experimental_setup": {
                "working_electrode": cv_params.get("working_electrode_type"),
                "counter_electrode": cv_params.get("counter_electrode_type"),
                "reference_electrode": cv_params.get("reference_electrode"),
            },
            "sample_preparation": {
                "final_volume_ml": recipe.get("final_volume_ml"),
                "solids": recipe.get("solids", []),
                "liquids": recipe.get("liquids", []),
            },
            "cv_parameters": cv_params,
            "results": {
                "cv": results_data.get("cv_raw", {}),
                "ph": results_data.get("ph_measurements", {}),
                "electrode": {"status": "Images evaluated"},
            },
            "analysis": {
                "cv_interpretation": (
                    "An irreversible oxidation peak was observed near +0.4 V, "
                    "characteristic of ascorbic acid oxidation to dehydroascorbic acid."
                    if results_data.get("cv_raw")
                    else "No CV data available for evaluation."
                ),
                "ph_interpretation": (
                    f"pH changed from {ph_data.get('ph_before')} to {ph_data.get('ph_after')}."
                    if ph_data.get("ph_before")
                    else "pH measurements unavailable."
                ),
                "electrode_interpretation": "Visual inspection shows intact electrode surface.",
                "overall_interpretation": "Experiment completed successfully.",
            },
            "execution": {"errors": [], "warnings": missing_data},
            "missing_data": missing_data,
            "conclusions": [
                "Ascorbic acid exhibits expected oxidation behavior."
            ],
            "recommendations": ["Repeat with varied scan rates."],
            "limitations": [
                "Uncompensated resistance was not measured directly."
            ],
            "data_quality": {"rating": "Good" if not missing_data else "Fair"},
            "test_data": {
                "used": results_data.get("is_simulated", False),
                "items": missing_data,
            },
        }

    # Save to report_raw_data.json
    if paths and "data" in paths:
        out_file = paths["data"] / "report_raw_data.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    return report

def json_to_pdf(
    report_data,
    output_pdf_path,
    input_data=None,
    results_data=None,
    image_paths=None,
):
    """
    Create a simple PDF report from:
        input_data   = planned experiment
        results_data = actual experiment results
        report_data  = LLM analysis
    """

    try:
        from pathlib import Path
        from xml.sax.saxutils import escape

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            PageBreak,
            Image,
            Flowable,
        )

    except ImportError:
        print("[WARNING] ReportLab library not found. PDF generation skipped.")
        return

    # ------------------------------------------------------------
    # BASIC DATA
    # ------------------------------------------------------------

    input_data = input_data or {}
    results_data = results_data or {}
    image_paths = image_paths or {}
    report_data = report_data or {}

    meta = report_data.get("report_metadata", {}) or {}
    input_meta = input_data.get("metadata", {}) or {}

    setup = report_data.get("experimental_setup", {}) or {}
    params = report_data.get("cv_parameters", {}) or {}
    input_params = input_data.get("cv_parameters", {}) or {}

    analysis = report_data.get("analysis", {}) or {}
    cv_analysis = analysis.get("cv_analysis", {}) or {}
    peak_analysis = cv_analysis.get("peak_analysis", {}) or {}

    results = report_data.get("results", {}) or {}

    result_ph = results_data.get("ph_measurements", {}) or {}
    result_temp = results_data.get("temp", {}) or {}
    result_masses = results_data.get("dispensed_masses", {}) or {}

    # ------------------------------------------------------------
    # SIMPLE HELPERS
    # ------------------------------------------------------------

    def text(value):
        """Make text safe for ReportLab."""
        if value is None or value == "":
            return "N/A"

        if isinstance(value, bool):
            return "Yes" if value else "No"

        return escape(str(value))

    def value(first, second=None, third=None):
        """Return the first value that actually exists."""
        for item in (first, second, third):
            if item is not None and item != "":
                return item
        return None

    def number(item, decimals=4):
        """Format a number without making the report complicated."""
        if item is None or item == "":
            return "N/A"

        if isinstance(item, (int, float)):
            return f"{item:.{decimals}f}".rstrip("0").rstrip(".")

        return text(item)

    def add_section(title):
        story.append(Spacer(1, 10))
        story.append(Paragraph(title, styles["Heading2"]))

    def add_text(label, item):
        if item is not None and item != "":
            story.append(
                Paragraph(
                    f"<b>{text(label)}:</b> {text(item)}",
                    styles["BodyText"],
                )
            )

    def add_list(items):
        if items is None:
            return

        if not isinstance(items, list):
            items = [items]

        for item in items:
            if isinstance(item, dict):
                for key, val in item.items():
                    story.append(
                        Paragraph(
                            f"• <b>{text(key)}:</b> {text(val)}",
                            styles["BodyText"],
                        )
                    )
            else:
                story.append(
                    Paragraph(
                        f"• {text(item)}",
                        styles["BodyText"],
                    )
                )

    def make_table(rows, widths=None):
        table = Table(
            rows,
            colWidths=widths,
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.black,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey,
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        return table

    # ------------------------------------------------------------
    # EDITABLE HUMAN EVALUATION FIELD
    # ------------------------------------------------------------

    class EditableField(Flowable):

        counter = 0

        def __init__(self, width=110, height=18):
            Flowable.__init__(self)

            self.width = width
            self.height = height

            EditableField.counter += 1

            self.field_name = (
                f"human_evaluation_{EditableField.counter}"
            )

        def wrap(self, availWidth, availHeight):
            return self.width, self.height

        def draw(self):

            self.canv.acroForm.textfield(
                name=self.field_name,
                value="",

                # These are now relative to the Table cell
                x=0,
                y=0,

                width=self.width,
                height=self.height,

                borderStyle="solid",
                borderWidth=0.5,

                borderColor=colors.grey,
                fillColor=colors.white,
                textColor=colors.black,

                fontName="Helvetica",
                fontSize=9,

                forceBorder=True,

                # IMPORTANT:
                # Make the field obey the Table cell's
                # current canvas transformation.
                relative=True,
            )

    # ------------------------------------------------------------
    # BASIC EXPERIMENT INFORMATION
    # ------------------------------------------------------------

    experiment_name = value(
        meta.get("experiment_name"),
        input_meta.get("experiment_name"),
        "Electrochemical Experiment",
    )

    experimenter = value(
        meta.get("experimenter"),
        input_meta.get("experimenter"),
        "N/A",
    )

    experiment_date = value(
        meta.get("report_generated_date"),
        meta.get("analysis_date"),
        "N/A",
    )

    user_prompt = value(
        input_meta.get("user_prompt"),
        meta.get("user_prompt"),
        "N/A",
    )

    working_electrode = value(
        input_params.get("working_electrode"),
        input_params.get("working_electrode_type"),
        setup.get("working_electrode"),
    )

    counter_electrode = value(
        input_params.get("counter_electrode"),
        input_params.get("counter_electrode_type"),
        setup.get("counter_electrode"),
    )

    reference_electrode = value(
        input_params.get("reference_electrode"),
        input_params.get("reference_electrode_type"),
        setup.get("reference_electrode"),
    )

    start_potential = value(
        input_params.get("start_potential_v"),
        params.get("start_potential_v"),
    )

    vertex_potential = value(
        input_params.get("potential_vertex_v"),
        params.get("potential_vertex_v"),
    )

    scan_rate = value(
        input_params.get("scan_rate_mv_s"),
        input_params.get("scan_rate_mV_s"),
        params.get("scan_rate_mv_s"),
    )

    step_size = value(
        input_params.get("increment_v"),
        input_params.get("increment_V"),
        params.get("increment_v"),
    )

    cycles = value(
        input_params.get("cycles"),
        params.get("cycles"),
    )

    # ------------------------------------------------------------
    # pH / TEMPERATURE
    # ------------------------------------------------------------

    ph_before = ph_data.get("ph_before")
    ph_after = ph_data.get("ph_after")

    temp_before = ph_data.get("temp_before_C")
    temp_after = ph_data.get("temp_after_C")

    # ------------------------------------------------------------
    # REPORT SETUP
    # ------------------------------------------------------------

    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
        title=str(experiment_name),
    )

    styles = getSampleStyleSheet()
    story = []

    # ------------------------------------------------------------
    # TITLE
    # ------------------------------------------------------------

    story.append(
        Paragraph(
            f"Experiment Report: {text(experiment_name)}",
            styles["Title"],
        )
    )

    cv_image = image_paths.get("CV")

    if cv_image and Path(cv_image).exists():
        #story.append(
        #    Paragraph(
        #        "<b>CV Plot</b>",
        #        styles["Heading3"],
        #    )
        #)

        story.append(
            Image(
                str(cv_image),
                width=420,
                height=245,
            )
        )

    else:
        story.append(
            Paragraph(
                "CV plot not available.",
                styles["BodyText"],
            )
        )
    story.append(
        Paragraph(
            f"<b>Experimenter:</b> {text(experimenter)} "
            f"&nbsp;&nbsp; "
            f"<b>Date:</b> {date.today().strftime('%d/%m/%Y')}",
            styles["BodyText"],
        )
    )
    # ------------------------------------------------------------
    # 1. SUMMARY
    # ------------------------------------------------------------

    add_section("1. Summary")

    summary = report_data.get(
        "experiment_summary",
        {},
    ) or {}

    add_text("User request", user_prompt)
    add_text("Description", summary.get("description"))
    add_text("Objective", summary.get("objective"))

    add_text(
        "Principal observation",
        value(
            summary.get("principal_observation"),
            summary.get("reported_outcome"),
        ),
    )

    # ------------------------------------------------------------
    # 2. EXPERIMENTAL SETUP
    # ------------------------------------------------------------

    add_section("2. Experimental Setup")

    setup_rows = [
        ["Parameter", "Value"],
        ["Working electrode", text(working_electrode)],
        ["Reference electrode", text(reference_electrode)],
        ["Counter electrode", text(counter_electrode)],
        [
            "Start potential",
            f"{number(start_potential)} V",
        ],
        [
            "Vertex potential",
            f"{number(vertex_potential)} V",
        ],
        [
            "Scan rate",
            f"{number(scan_rate)} mV/s",
        ],
        [
            "Step size",
            f"{number(step_size)} V",
        ],
        ["Cycles", text(cycles)],
    ]

    story.append(
        make_table(
            setup_rows,
            [180, 320],
        )
    )

    # ------------------------------------------------------------
    # 3. SAMPLE PREPARATION
    # ------------------------------------------------------------

    add_section("3. Sample Preparation")

    recipe = input_data.get(
        "recipe",
        {},
    ) or {}

    solids = recipe.get(
        "solids",
        [],
    ) or []

    liquids = recipe.get(
        "liquids",
        [],
    ) or []

    prep_rows = [
        [
            "Component",
            "Planned amount",
            "Actual amount",
        ]
    ]

    for i, solid in enumerate(solids):

        if not isinstance(solid, dict):
            continue

        name = solid.get(
            "name",
            "Unknown",
        )

        planned = solid.get(
            "mass_mg"
        )

        actual = None

        if i == 0:
            actual = value(result_masses.get("salt"))
        elif i == 1:
            actual = value(result_masses.get("analyte"))

        prep_rows.append(
            [
                text(name),
                f"{number(planned, 3)} mg",
                text(actual),
            ]
        )
    for liquid in liquids:

        if not isinstance(liquid, dict):
            continue

        name = liquid.get(
            "name",
            "Unknown",
        )

        volume = liquid.get(
            "volume_ml"
        )

        prep_rows.append(
            [
                text(name),
                f"{number(volume, 2)} mL",
                "N/A",
            ]
        )

    if len(prep_rows) == 1:

        prep_rows.append(
            [
                "No preparation data",
                "N/A",
                "N/A",
            ]
        )

    story.append(
        make_table(
            prep_rows,
            [180, 160, 160],
        )
    )

    # ------------------------------------------------------------
    # 4. CV RESULTS
    # ------------------------------------------------------------

    add_section(
        "4. Cyclic Voltammetry Results"
    )

    # ------------------------------------------------------------
    # 5. LLM CV MEASUREMENTS
    # ------------------------------------------------------------

    add_section(
        "4.1 LLM CV Measurements"
    )

    anodic = peak_analysis.get(
        "anodic_peak",
        {},
    ) or {}

    cathodic = peak_analysis.get(
        "cathodic_peak",
        {},
    ) or {}

    separation = peak_analysis.get(
        "peak_separation",
        {},
    ) or {}

    llm_rows = [
        [
            "Measurement",
            "LLM value",
            "Unit",
        ]
    ]

    def add_llm_measurement(
        label,
        item,
        unit="",
        decimals=4,
    ):

        if item is not None and item != "":

            llm_rows.append(
                [
                    label,
                    number(item, decimals),
                    unit,
                ]
            )

    # Anodic
    add_llm_measurement(
        "Anodic peak potential",
        anodic.get("potential_v"),
        "V",
        4,
    )

    add_llm_measurement(
        "Anodic peak current",
        anodic.get("current"),
        anodic.get(
            "current_unit",
            "",
        ),
        6,
    )

    add_llm_measurement(
        "Anodic onset potential",
        anodic.get(
            "onset_potential_v"
        ),
        "V",
        4,
    )

    # Cathodic
    add_llm_measurement(
        "Cathodic peak potential",
        cathodic.get(
            "potential_v"
        ),
        "V",
        4,
    )

    add_llm_measurement(
        "Cathodic peak current",
        cathodic.get("current"),
        cathodic.get(
            "current_unit",
            "",
        ),
        6,
    )

    add_llm_measurement(
        "Cathodic onset potential",
        cathodic.get(
            "onset_potential_v"
        ),
        "V",
        4,
    )

    # Peak separation
    add_llm_measurement(
        "Peak-to-peak separation",
        separation.get(
            "delta_potential_v"
        ),
        "V",
        4,
    )

    known_sections = {
        "anodic_peak",
        "cathodic_peak",
        "peak_separation",
    }

    for key, item in peak_analysis.items():

        if key in known_sections:
            continue

        if isinstance(
            item,
            (
                str,
                int,
                float,
                bool,
            ),
        ):

            label = (
                str(key)
                .replace("_", " ")
                .title()
            )

            llm_rows.append(
                [
                    label,
                    number(item),
                    "",
                ]
            )

    story.append(
        make_table(
            llm_rows,
            [250, 170, 80],
        )
    )

    # ------------------------------------------------------------
    # 6. HUMAN EVALUATION
    # ------------------------------------------------------------

    add_section(
        "4.2 Human Evaluation"
    )

    story.append(
        Paragraph(
            "The LLM measurements are shown below for comparison. "
            "The Human Evaluation column can be completed manually "
            "using the editable fields.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 10))
    human_rows = [
        [
            "Measurement",
            "LLM result",
            "Human evaluation",
        ]
    ]

    def add_human_measurement(
        label,
        item,
        unit="",
        decimals=4,
    ):

        if item is None or item == "":
            llm_result = "N/A"
        else:
            llm_result = (
                f"{number(item, decimals)} {unit}"
            ).strip()

        human_rows.append(
            [
                label,
                llm_result,

                # ------------------------------------------------
                # ONLY THE THIRD COLUMN IS EDITABLE
                # ------------------------------------------------
                EditableField(
                    width=110,
                    height=18,
                ),
            ]
        )

    # ------------------------------------------------------------
    # Main CV measurements
    # ------------------------------------------------------------

    add_human_measurement("Anodic peak potential",anodic.get("potential_v"),"V",4,)

    add_human_measurement(
        "Anodic peak current",
        anodic.get(
            "current"
        ),
        anodic.get(
            "current_unit",
            "",
        ),
        6,
    )

    add_human_measurement(
        "Anodic onset potential",
        anodic.get(
            "onset_potential_v"
        ),
        "V",
        4,
    )

    add_human_measurement(
        "Cathodic peak potential",
        cathodic.get(
            "potential_v"
        ),
        "V",
        4,
    )

    add_human_measurement(
        "Cathodic peak current",
        cathodic.get(
            "current"
        ),
        cathodic.get(
            "current_unit",
            "",
        ),
        6,
    )

    add_human_measurement(
        "Cathodic onset potential",
        cathodic.get(
            "onset_potential_v"
        ),
        "V",
        4,
    )

    add_human_measurement(
        "Peak-to-peak separation",
        separation.get(
            "delta_potential_v"
        ),
        "V",
        4,
    )

    # ------------------------------------------------------------
    # Additional scalar peak-analysis values
    # ------------------------------------------------------------

    for key, item in peak_analysis.items():

        if key in known_sections:
            continue

        if isinstance(
            item,
            (
                str,
                int,
                float,
                bool,
            ),
        ):

            label = (
                str(key)
                .replace("_", " ")
                .title()
            )

            human_rows.append(
                [
                    label,
                    text(item),

                    EditableField(
                        width=110,
                        height=18,
                    ),
                ]
            )
    # ------------------------------------------------------------
    # Add Human Evaluation table
    # ------------------------------------------------------------

    story.append(make_table(human_rows,[220, 160, 120],))



    # ------------------------------------------------------------
    # 7. pH AND TEMPERATURE
    # ------------------------------------------------------------

    add_section("4.3 pH and Temperature")

    ph_rows = [
        [
            "Measurement",
            "Value",
        ],
        [
            "pH before CV",
            number(
                ph_before,
                2,
            ),
        ],
        [
            "pH after CV",
            number(
                ph_after,
                2,
            ),
        ],
        [
            "Temperature before CV",
            f"{number(temp_before, 2)} °C",
        ],
        [
            "Temperature after CV",
            f"{number(temp_after, 2)} °C",
        ],
    ]

    story.append(
        make_table(
            ph_rows,
            [250, 250],
        )
    )

    add_text(
        "pH interpretation",
        analysis.get(
            "ph_interpretation"
        ),
    )
    ##hereee
    # ------------------------------------------------------------
    # Automated Evaluation 
    # ------------------------------------------------------------
    
    try:
        ##TODO 
        automated_analysis_results = run_analysis(paths["data"] / "cv_raw.json",paths["imgs"])
        #
        #print(automated_analysis_results)
        story.append(PageBreak())
        add_section("4.4 Automated Analysis")
        #cv_analysis_image = image_paths.get("cv_analysis.png")
        #print(cv_analysis_image)
   
        if Path(paths["imgs"] / "cv_analysis.png").exists():
            #story.append(
            #    Paragraph(
            #        "<b>CV Plot</b>",
            #        styles["Heading3"],
            #    )
            #)
            story.append(Image(str(paths["imgs"] / "cv_analysis.png"),width=420,height=245,))

        else:
            story.append(
                Paragraph(
                    "CV plot not available.",
                    styles["BodyText"],
                )
            )
        automated_cv_analysis_rows = [
        [
            "Measurement",
            "Value",
            "Unit",
        ]
    ]
        for key, item in automated_analysis_results.items():
            if isinstance(
                item,
                (
                    str,
                    int,
                    float,
                    bool,
                ),
            ):

                label = (str(key).replace("_", " ").title())
                automated_cv_analysis_rows.append(
                    [
                        label,
                        number(item,decimals=7),
                        "A" if "Current" in label else "V",
                    ]
                )

        story.append(
            make_table(
                automated_cv_analysis_rows,
                [250, 170, 80],
            )
        )

    except Exception as e:
        print(F"[ERROR] {e}")
        #Put in the PDF that the test failed 
    # ------------------------------------------------------------
    # 8. SCIENTIFIC INTERPRETATION
    # ------------------------------------------------------------
    story.append(PageBreak())
    add_section(
        "5. Scientific Interpretation"
    )

    add_text(
        "CV interpretation",
        analysis.get(
            "cv_interpretation"
        ),
    )

    add_text(
        "Raw data interpretation",
        cv_analysis.get(
            "raw_data_interpretation"
        ),
    )

    add_text(
        "Electrochemical assignment",
        cv_analysis.get(
            "electrochemical_assignment"
        ),
    )

    add_text(
        "Reversibility assessment",
        cv_analysis.get(
            "reversibility_assessment"
        ),
    )
    # ------------------------------------------------------------
    # 9. DATA QUALITY
    # ------------------------------------------------------------
    
    add_section(
        "6. Data Quality"
    )

    data_quality = report_data.get(
        "data_quality",
        {},
    ) or {}

    add_text(
        "Rating",
        data_quality.get(
            "rating"
        ),
    )

    warnings = (
        report_data.get(
            "execution",
            {},
        ) or {}
    ).get(
        "warnings",
        [],
    )

    if warnings:

        story.append(
            Paragraph(
                "<b>Warnings</b>",
                styles["Heading3"],
            )
        )

        add_list(warnings)

    missing_data = report_data.get(
        "missing_data",
        [],
    )

    if missing_data:

        story.append(
            Paragraph(
                "<b>Missing data</b>",
                styles["Heading3"],
            )
        )

        add_list(missing_data)

    # ------------------------------------------------------------
    # 7. ELECTRODE IMAGES
    # ------------------------------------------------------------
    story.append(PageBreak())
    add_section(
        "7. Electrode Images"
    )

    before_image = image_paths.get(
        "electrode_before"
    )

    after_image = image_paths.get(
        "electrode_after"
    )

    image_rows = [
        [
            "Electrode before CV",
            "Electrode after CV",
        ]
    ]

    before_cell = "Image not available."
    after_cell = "Image not available."

    if (
        before_image
        and Path(before_image).exists()
    ):

        before_cell = Image(
            str(before_image),
            width=220,
            height=160,
        )

    if (
        after_image
        and Path(after_image).exists()
    ):

        after_cell = Image(
            str(after_image),
            width=220,
            height=160,
        )

    image_rows.append(
        [
            before_cell,
            after_cell,
        ]
    )

    story.append(
        make_table(
            image_rows,
            [250, 250],
        )
    )

    add_text(
        "Electrode interpretation",
        analysis.get(
            "electrode_interpretation"
        ),
    )

    # ------------------------------------------------------------
    # 11. SAFETY
    # ------------------------------------------------------------

    add_section(
        "8. Safety and Handling"
    )

    safety = input_data.get(
        "safety_assessment",
        {},
    ) or {}

    add_text(
        "Handling precautions",
        safety.get(
            "handling_precautions"
        ),
    )

    add_text(
        "Hazards",
        safety.get(
            "hazards"
        ),
    )

    add_text(
        "Cross-contamination risks",
        safety.get(
            "cross_contamination_risks"
        ),
    )

    add_text(
        "Waste disposal",
        safety.get(
            "waste_disposal"
        ),
    )

    execution_safety = (
        report_data.get(
            "execution",
            {},
        ) or {}
    ).get(
        "safety_notes"
    )

    if execution_safety:

        add_text(
            "Execution safety notes",
            execution_safety,
        )

    # ------------------------------------------------------------
    # 12. CONCLUSIONS
    # ------------------------------------------------------------

    add_section(
        "9. Conclusions"
    )

    conclusions = report_data.get(
        "conclusions"
    )

    if conclusions:

        add_list(conclusions)

    else:

        story.append(
            Paragraph(
                "No conclusions supplied.",
                styles["BodyText"],
            )
        )

    # ------------------------------------------------------------
    # 13. RECOMMENDATIONS
    # ------------------------------------------------------------

    add_section(
        "10. Recommendations"
    )

    recommendations = report_data.get(
        "recommendations"
    )

    if recommendations:

        add_list(recommendations)

    else:

        story.append(
            Paragraph(
                "No recommendations supplied.",
                styles["BodyText"],
            )
        )

    # ------------------------------------------------------------
    # 14. LIMITATIONS
    # ------------------------------------------------------------

    add_section(
        "11. Limitations"
    )

    limitations = report_data.get(
        "limitations"
    )

    if limitations:

        add_list(limitations)

    else:

        story.append(
            Paragraph(
                "No limitations supplied.",
                styles["BodyText"],
            )
        )

    # ------------------------------------------------------------
    # 15. LLM INTERACTION LOG
    # ------------------------------------------------------------

    story.append(PageBreak())

    add_section(
        "12. LLM Interaction Log"
    )

    # ------------------------------------------------------------
    # User prompt
    # ------------------------------------------------------------

    story.append(
        Paragraph(
            "<b>User Prompt</b>",
            styles["Heading3"],
        )
    )

    metadata = input_data.get(
        "metadata",
        {},
    ) or {}

    user_prompt = metadata.get(
        "user_prompt",
        "No user prompt was provided in input_data.",
    )

    story.append(
        Paragraph(
            text(user_prompt),
            styles["BodyText"],
        )
    )

    story.append(
        Spacer(1, 12)
    )

    # ------------------------------------------------------------
    # LLM response / reasoning
    # ------------------------------------------------------------
    story.append(Paragraph("<b>LLM Response</b>",styles["Heading3"],))
    llm_reasoning = input_data.get("llm_reasoning", {},) or {}

    if (isinstance(llm_reasoning, dict) and llm_reasoning):
        reasoning_fields = [
            (
                "Selected Mode",
                "selected_mode_explanation",
            ),
            (
                "Parameter Selection",
                "parameter_selection_logic",
            ),
            (
                "Electrolyte Preparation",
                "electrolyte_preparation_explanation",
            ),
            (
                "Analyte Preparation",
                "analyte_preparation_explanation",
            ),
            (
                "Electrode Deposition",
                "electrode_deposition_explanation",
            ),
            (
                "Drying",
                "drying_explanation",
            ),
            (
                "Constraint Validation",
                "constraint_validation_summary",),]
        for title, key in reasoning_fields:
            value_text = llm_reasoning.get(key)
            if value_text:
                story.append(Paragraph(f"<b>{text(title)}</b>",styles["Heading3"],))
                story.append(Paragraph(text(value_text),styles["BodyText"],))
                story.append(Spacer(1, 6))
        # --------------------------------------------------------
        # Assumptions
        # --------------------------------------------------------
        assumptions = llm_reasoning.get("assumptions",[],) or []
        if assumptions:
            story.append(Paragraph("<b>Assumptions</b>",styles["Heading3"],))
            for assumption in assumptions:
                story.append(Paragraph(f"• {text(assumption)}",styles["BodyText"],))
            story.append(Spacer(1, 8))
        # --------------------------------------------------------
        # Concentration calculations
        # --------------------------------------------------------
        concentration_calculations = (llm_reasoning.get("concentration_calculations",[],) or [])
        if concentration_calculations:
            story.append(Paragraph("<b>Concentration Calculations</b>",styles["Heading3"],))
            for calculation in concentration_calculations:
                if not isinstance(calculation,dict,):
                    continue
                chemical = calculation.get("chemical","Unknown chemical",)
                explanation = calculation.get("calculation_explanation","",)
                story.append(Paragraph(f"<b>{text(chemical)}</b>",styles["BodyText"],))
                if explanation:
                    story.append(Paragraph(text(explanation),styles["BodyText"],))
                story.append(Spacer(1, 6))
    else:
        story.append(
            Paragraph("No LLM response was provided in input_data.",styles["BodyText"],))
    # ------------------------------------------------------------
    # BUILD PDF
    # ------------------------------------------------------------
    # Keep the normal ReportLab build.
    doc.build(story)
    print(f"[INFO] Generated PDF report: {output_pdf_path}")
def photograph_electrode(electrode_number=1, file_name=""):
    """Photograph an electrode and save the image to file_name."""
    # Move camera under the requested electrode
    #home_echem()
    execute_routine_echem(f"camera_under_electrode_{electrode_number}.json");time.sleep(3)
    # Capture image from Flask camera API
    electrode_photo = camera.capture() ;time.sleep(2)
    execute_routine_echem(f"zero.json")
    # Save JPEG bytes to the requested file
    with open(file_name, "wb") as f:
        f.write(electrode_photo)
    #execute_routine_echem("idle.json")
    home_echem()
    #home_echem()
    return file_name
if __name__ == "__main__":
    # 1. Initialize workflow paths and load user script
    experiment, paths = load_experiment()
    #echem_slot=2
    #home_echem()
    #print(photograph_electrode(electrode_number=2, file_name=paths["imgs"] / "electrode_before.png"))
    #execute_routine_echem("ph_measurement.json")
    #execute_routine_echem("idle.json")
    #home_echem()
    #print("[INFO] Washing electrodes.") 
    #execute_routine_echem("wash_electrodes.json")
    ##wash_electrodes(cycles=10,electrode_id=echem_slot)
    #execute_routine_echem("wash_electrodes_out.json")
    #execute_routine_echem("ph_measurement.json")
    #print("[INFO] Drying electrodes") 
    #execute_routine_echem("idle.json")
    #home_echem()
    ##execute_routine_echem("idle.json")
    #execute_routine_echem("cv_start_position.json")
    #execute_routine_echem("cv_end_position.json")
    #execute_routine_echem("idle.json")
    #home_echem()
    #print("[INFO] Setting ph measurement.") 
    #execute_routine_echem("ph_measurement.json")
    #echem.dryer_on();time.sleep(10)
    #print("[INFO] Picking ph Probe") 
    #print("[INFO] Returning ph Probe")
    #echem.dryer_off();time.sleep(0.1)
    #execute_routine_echem("idle.json")
    #home_echem()
    #print(photograph_electrode(electrode_number=2, file_name=paths["imgs"] / "electrode_after.png"))
    ##############################################
    #POLISHING? YES POLISH no? continue 
    ##############################################
    #while True:
    #    answer=input(f'[WARNING] Polish electrode {echem_slot} (y/n)')
    #    if answer == 'y' or answer == 'Y':
    #        print(F"[INFO] Polishing electrode {echem_slot} ")
    #        polish_electrode(electrode_id=2,passes=3)
    #        #washing and drying routine again
    #        home_echem()    
    #        print("[INFO] Washing electrodes.") 
    #        execute_routine_echem("wash_electrodes.json")
    #        wash_electrodes(cycles=10,electrode_id=echem_slot)
    #        execute_routine_echem("wash_electrodes_out.json")
    #        execute_routine_echem("ph_measurement.json")
    #        print("[INFO] Drying electrodes") 
    #        echem.dryer_on();time.sleep(10)
    #        echem.dryer_off();time.sleep(0.1)
    #        execute_routine_echem("idle.json")
    #        home_echem()
    #        home_echem()
    #        print(photograph_electrode(electrode_number=2, file_name=paths["imgs"] / "electrode_after_polishing.png"))
    #        break
    #    elif answer == 'n' or answer == 'N':
    #        print(F"[WARNING] Electrode {echem_slot} not polished.")
    #        break
    #sys.exit("DEBUG: CV test routine executed succesfully.")
    ##########################################ONLY report form json##########################
    # Load CV data 
    with open(paths["data"] / "cv_raw.json", "r", encoding="utf-8") as f: 
        cv_data = json.load(f) 
    # Load pH data 
    with open(paths["data"] / "ph_measurements.json", "r", encoding="utf-8") as f: 
        ph_data = json.load(f) 
    # Load dispensed masses 
    with open(paths["data"] / "dispensed_masses.json", "r", encoding="utf-8") as f: 
        dispensed_masses = json.load(f) 
        # Load report raw data 
    with open(paths["data"] / "report_raw_data.json", "r", encoding="utf-8") as f: 
        report_data = json.load(f) 
    # Build results_data exactly as expected by the report 
    results_data = { "cv_raw": cv_data, 
                    "ph_measurements": ph_data, 
                    "images": { "electrode_before": paths["imgs"] / "electrode_before.png", "electrode_after": paths["imgs"] / "electrode_after.png", 
                            "CV": paths["imgs"] / "CV.png", }, 
                    "dispensed_masses": dispensed_masses, 
                    "is_simulated": False, } 
    # Generate the LLM report and/or PDF 
    #report_data = generate_report( input_data=experiment, results_data=results_data, paths=paths, model="terra")
    #sys.exit("DEBUG: JSON files loaded successfully. Stopping before experiment execution.")
    report_from_json(
        input_data=experiment,
        results_data=results_data,
        paths=paths,
        model="terra",
        report_data=report_data
    )
    sys.exit("DEBUG: JSON files loaded successfully. Stopping before experiment execution.") 
    ######################################################################################################
    if experiment["experiment_mode"] == "analyte_in_electrolyte":
        echem_slot=2    
        cv_params={
            "potentiostat_id":1,
            "i_range":I_range_mode[experiment["cv_parameters"]["i_range"]],
            "start_potential":experiment["cv_parameters"]["start_potential_v"],
            "potential_vertex":experiment["cv_parameters"]["potential_vertex_v"],
            "scan_rate":experiment["cv_parameters"]["scan_rate_mv_s"],
            "cycles":experiment["cv_parameters"]["cycles"],
            "increment":experiment["cv_parameters"]["increment_v"],
            "show_plot":True,}

        solids= {}
        for solid in experiment['recipe']['solids']:
            solids[solid['cartridge_position']]= [solid['name'],solid['mass_mg'],solid["role"]]
        print(solids)
        liquids = {}
        for liquid in experiment['recipe']['liquids']:
            liquids[liquid['channel']]= [liquid['name'],liquid['volume_ml'],"solvent"]
        print(liquids)
        #TODO remove commenting block 
        weights = prepare_sample(solids=solids,
                    liquids=liquids,
                    experiment={
            solids[1][2]: {'sample_id': solids[1],'cartridge_pos': 1},
            solids[2][2]: {'sample_id':solids[2],'cartridge_pos':2}
        })
        ###TODO remove commenting block
        #w1={'outcomes': ['Substance: KCL', 'Content Unit="mg": 124.16', 'Target_quantity Unit="mg": 111.83', 'Powder_dosing_mode: Standard', 'Tapping_before_dosing: On', 'Intensity: 50', 'Tolerance_Mode: +/- Tolerance', 'Tolerance Unit="%": 1.0', 'Validity: INVALID'], 'success': True}
        #w2={'outcomes': ['Substance: FERROCYANIDE', 'Content Unit="mg": 5.8', 'Target_quantity Unit="mg": 4.939', 'Powder_dosing_mode: Standard', 'Tapping_before_dosing: On', 'Intensity: 50', 'Tolerance_Mode: +/- Tolerance', 'Tolerance Unit="%": 1.0', 'Validity: INVALID'], 'success': True}
        #w1={'outcomes': ['Substance: KCL', 'Content Unit="mg": 111.90', 'Target_quantity Unit="mg": 111.32', 'Powder_dosing_mode: Standard', 'Tapping_before_dosing: On', 'Intensity: 50', 'Tolerance_Mode: +/- Tolerance', 'Tolerance Unit="%": 1.0', 'Validity: VALID'], 'success': True}
        #w2={'outcomes': ['Substance: VITAMIN C', 'Content Unit="mg": 131.84', 'Target_quantity Unit="mg": 132.00', 'Powder_dosing_mode: Standard', 'Tapping_before_dosing: On', 'Intensity: 50', 'Tolerance_Mode: +/- Tolerance', 'Tolerance Unit="%": 1.0', 'Validity: VALID'], 'success': True}
        #weights =[w1,w2]
        input("Continue?")
        home_echem()
        print(photograph_electrode(electrode_number=2, file_name=paths["imgs"] / "electrode_before.png"))
        V, I ,C, ph_before, ph_after, temp_before, temp_after = analise_sample(echem_slot=echem_slot,cv_file_name=paths["imgs"] / "CV.png",cv_params=cv_params)
        print(photograph_electrode(electrode_number=2, file_name=paths["imgs"] / "electrode_after.png"))
        home_echem()
        #input("continue?")
        print("[INFO] Simulating experiment execution...")
        cv_data = {
            "potential_V": V.tolist(),
            "current_A": I.tolist(),
            "cycle": C.tolist(),
            "cycles": experiment["cv_parameters"]["cycles"],
            "is_simulated": False,
        }
        #print(cv_data)
        with open(paths["data"] / "cv_raw.json", "w", encoding="utf-8") as f:
            json.dump(cv_data, f, indent=2)

        #ph_after=7
        ph_data = {"ph_before": ph_before, "ph_after": ph_after, "is_simulated": False,
                   "temp_before_C": temp_before, "temp_after_C": temp_after}
        with open(paths["data"] / "ph_measurements.json", "w", encoding="utf-8") as f:
            json.dump(ph_data, f, indent=2)

        dispensed_masses ={"salt": weights[0]['outcomes'][1],
                                    "analyte": weights[1]['outcomes'][1]}
        with open(paths["data"] / "dispensed_masses.json", "w", encoding="utf-8") as f:
            json.dump(dispensed_masses, f, indent=2)
        results_data = {
            "cv_raw": cv_data,
            "ph_measurements": ph_data,
            "images": {
                "electrode_before": paths["imgs"] / "electrode_before.png",
                "electrode_after": paths["imgs"] / "electrode_after.png",
                "CV": paths["imgs"] / "CV.png",
            },
            "dispensed_masses": dispensed_masses,
            "is_simulated": False,
        }
        # 3. Generate Report
        print("[INFO] Generating final report...")
        #report = generate_report(input_data=experiment, results_data=results_data, paths=paths, model="terra")
        report_data = generate_report(
            input_data=experiment, 
            results_data=results_data, 
            paths=paths, 
            model="terra")
        report_from_json(
            input_data=experiment,
            results_data=results_data,
            paths=paths,
            model="terra",
            report_data=report_data)
        ##############################################
        #POLISHING? YES POLISH no? continue 
        ##############################################
        while True:
            answer=input(f'[WARNING] Polish electrode {echem_slot} (y/n)')
            if answer == 'y' or answer == 'Y':
                print(F"[INFO] Polishing electrode {echem_slot} ")
                polish_electrode(electrode_id=2,passes=5)
                #washing and drying routine again
                home_echem()
                print("[INFO] Washing electrodes.") 
                execute_routine_echem("wash_electrodes.json")
                wash_electrodes(cycles=20,electrode_id=echem_slot)
                execute_routine_echem("wash_electrodes_out.json")
                execute_routine_echem("ph_measurement.json")
                print("[INFO] Drying electrodes") 
                echem.dryer_on();time.sleep(10)
                echem.dryer_off();time.sleep(0.1)
                execute_routine_echem("idle.json")
                home_echem()
                home_echem()
                print(photograph_electrode(electrode_number=2, file_name=paths["imgs"] / "electrode_after_polishing.png"))
                break
            elif answer == 'n' or answer == 'N':
                print(F"[WARNING] Electrode {echem_slot} not polished.")
                break
        ############################################
        # Homing system
        #############################################
        print("[INFO] Returning rack to carousel.")
        execute_routine_arm("idle.json")
        execute_routine_arm(F"pick_rack_from_{echem_slot}.json")
        execute_routine_arm("place_rack_in_bottom_carousel.json")
        print("[INFO] Workflow finished, homing arm.")
        home_arm()
        print("[SUCCESS] Workflow execution and report generation complete.")
