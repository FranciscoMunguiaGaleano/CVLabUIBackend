from cvlab.devices import Arm, SolidDispenser 
from cvlab.utils.config import load_config
import os

CWD_PATH = os.getcwd()
CONF_PATH = os.getcwd()+"/data/conf/conf_dummy.json"

class DeviceManager:
    def __init__(self):
        config = load_config(CONF_PATH)
       
        self.arm = Arm(
            name="Arm",
            arm_url=config.ARM_URL,
            arm_aux_url=config.PLC_URL,
            arm_aux_port=config.PLC_PORT
        )
        self.solids_dispenser = SolidDispenser(
            name="Quantos",
            solid_dispenser_url=config.SOLIDS_URL,
            solid_dispenser_aux_url=config.PLC_URL,
            solid_dispenser_aux_port=config.PLC_PORT
        )

# Singleton instance
devices = DeviceManager()
