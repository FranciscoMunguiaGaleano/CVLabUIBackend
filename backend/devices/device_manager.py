from cvlab.devices import Arm, SolidDispenser, Mixer, Capper, PHMeter, SyringePump, TopCarousel, BottomCarousel 
from cvlab.utils.config import load_config
import os

CWD_PATH = os.getcwd()
CONF_PATH = os.getcwd()+"/data/conf/conf_dummy.json"
#CONF_PATH = os.getcwd()+"/data/conf/devices_urls.json"
PHMETER_CALIBRATION_CONF = os.getcwd()+"/data/calibration/ph_calibration.json"
TOP_CAROUSEL_CONF = os.getcwd()+"/data/routines/top_carousel/top_carousel.json"
BOTTOM_CAROUSEL_CONF = os.getcwd()+"/data/routines/bottom_carousel/bottom_carousel.json"

class DeviceManager:
    def __init__(self):
        config = load_config(CONF_PATH)
        self.arm = Arm(
            name="Arm",
            arm_url=config.ARM_URL,
            arm_aux_url=config.PLC_URL,
            arm_aux_port=config.PLC_PORT
        )
        self.capper = Capper(
            name="Capper",
            capper_url=config.PLC_URL,
            capper_port=config.PLC_PORT
        )
        self.solids_dispenser = SolidDispenser(
            name="Quantos",
            solid_dispenser_url=config.SOLIDS_URL,
            solid_dispenser_aux_url=config.PLC_URL,
            solid_dispenser_aux_port=config.PLC_PORT
        )
        self.mixer = Mixer(
        name="Mixer",
            mixer_url=config.PLC_URL,
            mixer_port=config.PLC_PORT,
            mixer_aux_url=config.PUMPS_URL,
            mixer_aux_port=config.PUMPS_PORT
        )
        self.ph_meter = PHMeter(
            name="pH Meter",
            phmeter_url=config.PH_PROBE_URL,
            phmeter_port=config.PH_PROBE_PORT,
            calibration_conf=PHMETER_CALIBRATION_CONF
        )
        self.liquids_dispenser = SyringePump(
            name="Liquids Pump",
            syringe_pump_url=config.LIQUIDS_URL,
            syringe_pump_aux_url=config.PLC_URL,
            syringe_pump_aux_port=config.PLC_PORT
        )
        self.top_carousel = TopCarousel(
            name="Top Carousel",
            carousel_url=config.TOP_CAROUSEL_URL,
            carousel_port=config.TOP_CAROUSEL_PORT,
            conf_file=TOP_CAROUSEL_CONF
        )
        self.bottom_carousel = BottomCarousel(
            name="Bottom Carousel",
            carousel_url=config.BOTTOM_CAROUSEL_URL,
            carousel_port=config.BOTTOM_CAROUSEL_PORT,
            aux_carousel_pump_url=config.PUMPS_URL,
            aux_carousel_pump_port=config.PUMPS_PORT,
            aux_carousel_purger_url=config.PLC_URL,
            aux_carousel_purger_port=config.PLC_PORT,
            conf_file=BOTTOM_CAROUSEL_CONF
        )


# Singleton instance
devices = DeviceManager()
