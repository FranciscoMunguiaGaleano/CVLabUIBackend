from flask import Flask
from flask_cors import CORS
from api.arm_api import robot_bp
from api.ai_api import ai_bp
from api.solids_dispenser_api import quantos_bp
from api.mixer_api import mixer_bp
from api.capper_api import capper_bp
from api.ph_api import phmeter_bp
from api.liquids_dispenser_api import liquids_dispenser_bp
from api.carousel_top_api import top_carousel_bp
from api.carousel_bottom_api import bottom_carousel_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(robot_bp, url_prefix="/api/v1/robot")
app.register_blueprint(ai_bp, url_prefix="/api/v1/aiscientist")
app.register_blueprint(quantos_bp, url_prefix="/api/v1/quantos")
app.register_blueprint(mixer_bp, url_prefix="/api/v1/mixer")
app.register_blueprint(capper_bp, url_prefix="/api/v1/capper")
app.register_blueprint(phmeter_bp, url_prefix="/api/v1/phmeter")
app.register_blueprint(liquids_dispenser_bp, url_prefix="/api/v1/liquids_dispenser")
app.register_blueprint(top_carousel_bp, url_prefix="/api/v1/top_carousel")
app.register_blueprint(bottom_carousel_bp, url_prefix="/api/v1/bottom_carousel")

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
