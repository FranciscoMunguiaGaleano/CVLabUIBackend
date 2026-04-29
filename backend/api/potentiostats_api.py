from flask import Blueprint, jsonify, request, send_file
from devices.device_manager import devices
import io

potentiostat_bp = Blueprint("potentiostat", __name__)

pstat = devices.potentiostats

# -----------------------------------
# DEVICE MAPPING
# -----------------------------------
DEVICE_MAP = {
    1: 0,
    2: 1,
    3: 2
}

# -----------------------------------
# STATUS
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/status", methods=["GET"])
def status(p_id):
    try:
        hw_id = DEVICE_MAP[p_id]
        msg = pstat.status(hw_id)
        return jsonify({"message": str(msg)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------------
# CYCLIC VOLTAMMETRY
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/cyclic_voltammetry", methods=["POST"])
def cyclic_voltammetry(p_id):
    try:
        hw_id = DEVICE_MAP[p_id]

        data = request.args  # KEEP QUERY PARAM STYLE

        # --- SAFE TYPE CONVERSION (THIS WAS MISSING BEFORE) ---
        i_range = data.get("i_range", 5)
        start_potential = float(data.get("start_potential", 0))
        potential_vertex = float(data.get("potential_vertex", 1))
        scan_rate = float(data.get("scan_rate", 100))
        cycles = int(data.get("cycles", 1))
        increment = float(data.get("increment", 0.01))

        result = pstat.cyclic_voltammetry(
            potentiostat_id=hw_id,
            i_range=i_range,
            start_potential=start_potential,
            potential_vertex=potential_vertex,
            scan_rate=scan_rate,
            cycles=cycles,
            increment=increment,
        )

        if result is None:
            return jsonify({"error": "Measurement failed"}), 500

        return send_file(
            io.BytesIO(result),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"cv_p{p_id}.csv"
        )

    except Exception as e:
        return jsonify({
            "error": "Cyclic voltammetry exception",
            "details": str(e)
        }), 500


# -----------------------------------
# LINEAR VOLTAMMETRY
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/linear_voltammetry", methods=["POST"])
def linear_voltammetry(p_id):
    try:
        hw_id = DEVICE_MAP[p_id]
        data = request.args

        result = pstat.linear_voltammetry(
            potentiostat_id=hw_id,
            i_range=data.get("i_range", 5),
            start_potential=float(data.get("start_potential", 0)),
            end_potential=float(data.get("end_potential", 1)),
            scan_rate=float(data.get("scan_rate", 100)),
            increment=float(data.get("increment", 0.01)),
        )

        if result is None:
            return jsonify({"error": "Measurement failed"}), 500

        return send_file(
            io.BytesIO(result),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"lv_p{p_id}.csv"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------------
# OPEN CIRCUIT
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/open_circuit", methods=["POST"])
def open_circuit(p_id):
    try:
        hw_id = DEVICE_MAP[p_id]
        data = request.args

        result = pstat.open_circuit(
            potentiostat_id=hw_id,
            duration=float(data.get("duration", 10)),
            sampling_period=float(data.get("sampling_period", 0.1)),
        )

        if result is None:
            return jsonify({"error": "Measurement failed"}), 500

        return send_file(
            io.BytesIO(result),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"ocp_p{p_id}.csv"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------------
# ELECTROLYSIS
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/electrolysis", methods=["POST"])
def electrolysis(p_id):
    try:
        hw_id = DEVICE_MAP[p_id]
        data = request.args

        result = pstat.electrolysis(
            potentiostat_id=hw_id,
            i_range=data.get("i_range", 5),
            potential=float(data.get("potential", 0.5)),
            duration=float(data.get("duration", 10)),
            sampling_period=float(data.get("sampling_period", 0.1)),
        )

        if result is None:
            return jsonify({"error": "Measurement failed"}), 500

        return send_file(
            io.BytesIO(result),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"electrolysis_p{p_id}.csv"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500