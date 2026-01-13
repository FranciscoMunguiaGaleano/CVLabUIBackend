from flask import Flask
from flask_cors import CORS
from api.arm_api import robot_bp
from api.ai_api import ai_bp
from api.solids_dispenser_api import quantos_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(robot_bp, url_prefix="/api/v1/robot")
app.register_blueprint(ai_bp, url_prefix="/api/v1/aiscientist")
app.register_blueprint(quantos_bp, url_prefix="/api/v1/quantos")

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
