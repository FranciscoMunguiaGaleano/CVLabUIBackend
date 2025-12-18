from backend.core.cvlab import Arm, Echem, Capper, SyringePump, SolidDispenser, Mixer, Carousel, BottomCarousel, pHmetter, load_config
import time 
import os
from pathlib import Path

CWD_PATH = os.getcwd()
CONF_PATH = CWD_PATH + '\\backend\\data\\conf\\'
ROUTINES_PATH = CWD_PATH + '\\backend\\data\\routines\\'
TOP_CAROUSEL_CONF = ROUTINES_PATH + 'top_carousel\\top_carousel.json'
BOTTOM_CAROUSEL_CONF = ROUTINES_PATH + 'bottom_carousel\\bottom_carousel.json'
PHMETER_CALIBRATION_CONF =  Path(CWD_PATH + '\\backend\\data\\calibration\\ph_calibration.json')

sample = {
        "sample_id": "Carbon",
        "mass": 50.0,
        "tolerance": 1.0,          # optional
        "algorithm": "standard",    # optional, "standard" or "advanced"
        "tapper_intensity": 50,     # optional
        "tapper_duration": 3        # optional
        }
liquid = {
        "liquid_id": "water",
        "volume": 2,
        "source_port": "I1",
        "destination_port": "O1",   
        "waste_port": "O3"
}

config = load_config(conf_file=CONF_PATH+'conf_dummy.json')
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
        name = "Liquids Pump",
        syrynge_pump_url=config.LIQUIDS_URL,
        syringe_pump_aux_port=config.PLC_PORT,
        syringe_pump_aux_url=config.PLC_PORT)

top_carousel = Carousel(
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

ph_meter = pHmetter(
    name="pH Meter",
    phmeter_url=config.PH_PROBE_URL,
    phmeter_port=config.PH_PROBE_PORT,
    calibration_conf=PHMETER_CALIBRATION_CONF
)

if config:
##############################################################
    print("<---------Debugging PhMetter---------->")
    print(ph_meter.read_status())
    ph_meter.read_ph()
    #exit()
############################################################## 
    print("<---------Debugging Bottom Carousel---------->")
    bottom_carousel.home();time.sleep(2)
    bottom_carousel.move_absolute(pos='2');time.sleep(0.1)
    bottom_carousel.turn_pumps_on()
    bottom_carousel.turn_pumps_off()
    bottom_carousel.turn_purger_on()
    bottom_carousel.turn_purger_off()
##############################################################
    print("<---------Debugging Top Carousel---------->")
    top_carousel.home();time.sleep(2)
    top_carousel.move_absolute(pos='4');time.sleep(0.5)
    top_carousel.move_absolute(pos='8');time.sleep(0.5)
    top_carousel.move_absolute(pos='18');time.sleep(0.5)
    top_carousel.move_incremental();time.sleep(0.2)
    
##############################################################
    print("<---------Debugging Liquid Dispenser---------->")
    liquids_dispenser.piston_to_dispense_position();time.sleep(0.3)
    liquids_dispenser.piston_to_home_position();time.sleep(0.3)
    liquids_dispenser.status();time.sleep(0.3)
    liquids_dispenser.get_valve_pos();time.sleep(0.3)
    liquids_dispenser.dispense(liquid);time.sleep(0.3)
    liquids_dispenser.move_home();time.sleep(0.3)
    liquids_dispenser.set_waste_port(liquid);time.sleep(0.3)
##############################################################
    print("<---------Debugging Solid Dispenser---------->")
    solids_dispenser.set_cartridge_tower_position(pos=1);time.sleep(0.3)
    solids_dispenser.set_cartridge_tower_position(pos=2);time.sleep(0.3)
    solids_dispenser.status();time.sleep(0.3)
    solids_dispenser.open_front_door();time.sleep(0.3)
    solids_dispenser.close_front_door();time.sleep(0.3)
    solids_dispenser.open_side_doors();time.sleep(0.3)
    solids_dispenser.close_side_doors();time.sleep(0.3)
    solids_dispenser.unlock_dosing_head();time.sleep(0.3)
    solids_dispenser.lock_dosing_head();time.sleep(0.3)
    solids_dispenser.get_sample_data();time.sleep(0.3)
    solids_dispenser.tare_balance();time.sleep(0.3)
    solids_dispenser.set_target_mass(sample);time.sleep(0.3)
    solids_dispenser.dispense(sample);time.sleep(0.3)
##############################################################
    print("<---------Debugging Mixer---------->")
    mixer.raise_lift();time.sleep(1)
    mixer.lower_lift();time.sleep(1)
    mixer.turn_ultrasound_bath_on();time.sleep(1)
    mixer.turn_ultrasound_bath_off();time.sleep(1)
    mixer.raise_lift();time.sleep(1)
############################################################
    print("<---------Debugging Arm---------->")
    arm.close_gripper();time.sleep(0.3)
    arm.close_gripper();time.sleep(0.3)
    arm.send_gcode('G1 X10');time.sleep(0.3)
    arm.unlock();time.sleep(0.3)
    arm.home();time.sleep(0.3)
    arm.settings();time.sleep(0.3)
    arm.sleep();time.sleep(0.3)
    arm.get_position();time.sleep(0.3)
    arm.status();time.sleep(0.3)
    arm.reset();time.sleep(0.3)
    arm.wait_until_idle();time.sleep(0.3)
    arm.execute_routine(file=ROUTINES_PATH+'arm\\pick_cartridge_from_tower_1.json');time.sleep(0.3)
##############################################################
    print("<---------Debugging Echem---------->")
    echem.send_gcode('G1 X10');time.sleep(0.3)
    echem.unlock();time.sleep(0.3)
    echem.home();time.sleep(0.3)
    echem.settings();time.sleep(0.3)
    echem.sleep();time.sleep(0.3)
    echem.get_position();time.sleep(0.3)
    echem.reset();time.sleep(0.3)
    echem.wait_until_idle();time.sleep(0.3)
    echem.execute_routine(file=ROUTINES_PATH+'echem\\pre_submerge_in_row_1.json');time.sleep(0.3)
    echem.polisher_on();time.sleep(0.3)
    echem.polisher_off();time.sleep(0.3)
    echem.polisher_dropper_on();time.sleep(0.3)
    echem.polisher_dropper_off();time.sleep(0.3)
    echem.dryer_on();time.sleep(0.3)
    echem.dryer_off();time.sleep(0.3)
    echem.purger_on();time.sleep(0.3)
    echem.purger_off();time.sleep(0.3)
    echem.polisher_set_speed('slow');time.sleep(0.3)
    echem.pipette_arm_home();time.sleep(0.3)
    echem.pipette_arm_unlock();time.sleep(0.3)
    echem.pipette_arm_sleep();time.sleep(0.3)
    echem.pipette_arm_reset();time.sleep(0.3)
    echem.pipete_arm_send_gcode(gcode="G90");time.sleep(0.3)
    echem.pipette_arm_execute_routine(file=ROUTINES_PATH+'pipette\\above_electrode_1.json');time.sleep(0.3)
    echem.pipette_home();time.sleep(0.3)
    echem.pipette_eject_tip();time.sleep(0.3)
    echem.pipette_preload();time.sleep(0.3)
    echem.pipette_load();time.sleep(0.3)
    echem.pipette_unload();time.sleep(0.3)
    echem.pipette_set_speed(speed='slow');time.sleep(0.3)
##############################################################
    print("<---------Debugging Capper---------->")
    capper.hold_vial()
    capper.uncap()
    capper.cap()
    capper.release_vial()

    





