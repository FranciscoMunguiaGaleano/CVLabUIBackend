from flask import Blueprint, jsonify, request, send_file
from devices.device_manager import devices
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import csv
from io import StringIO

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
# IN-MEMORY CACHE
# -----------------------------------
LAST_RESULTS = {}

# -----------------------------------
# GENERIC FIGURE BUILDER
# -----------------------------------
def making_figure(csv_bytes, title, xlabel, ylabel):
    try:
        if csv_bytes is None:
            raise RuntimeError("No data")

        csv_text = csv_bytes.decode("utf-8")
        csv_data = StringIO(csv_text)
        reader = csv.DictReader(csv_data)

        x = []
        y = []

        for row in reader:
            x.append(float(row[xlabel]))
            y.append(float(row[ylabel]))

        plt.figure()
        plt.plot(x, y)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        plt.grid()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        plt.close('all')
        img.seek(0)

        return img

    except Exception:
        return error_figure("Plot Error", xlabel, ylabel)


# -----------------------------------
# ERROR IMAGE
# -----------------------------------
def error_figure(title, xlabel, ylabel):
    plt.figure()
    plt.plot([0], [0], color='black')
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xlim(0, 1)
    plt.ylim(0, 1)

    img = io.BytesIO()
    plt.savefig(img, format='png')
    plt.close('all')
    img.seek(0)

    return img


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
# CYCLIC VOLTAMMETRY (CSV)
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/cyclic_voltammetry", methods=["POST"])
def cyclic_voltammetry(p_id):
    try:
        hw_id = DEVICE_MAP[p_id]
        data = request.args

        result = pstat.cyclic_voltammetry(
            potentiostat_id=hw_id,
            i_range=data.get("i_range", 5),
            start_potential=float(data.get("start_potential", 0)),
            potential_vertex=float(data.get("potential_vertex", 1)),
            scan_rate=float(data.get("scan_rate", 100)),
            cycles=int(data.get("cycles", 1)),
            increment=float(data.get("increment", 0.01)),
        )

        if result is None:
            LAST_RESULTS.pop((p_id, "cv"), None)
            return jsonify({"error": "Measurement failed"}), 500

        LAST_RESULTS[(p_id, "cv")] = result

        return send_file(
            io.BytesIO(result),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"cv_p{p_id}.csv"
        )

    except Exception as e:
        LAST_RESULTS.pop((p_id, "cv"), None)
        return jsonify({"error": str(e)}), 500


# -----------------------------------
# CYCLIC VOLTAMMETRY (PLOT)
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/cyclic_voltammetry/plot", methods=["GET"])
def cyclic_voltammetry_plot(p_id):
    key = (p_id, "cv")
    try:
        result = LAST_RESULTS.get(key)

        if result is None:
            img = error_figure("No CV Data", "Potential", "Current")
            return send_file(img, mimetype="image/png")

        img = making_figure(
            result,
            title=f"Cyclic Voltammetry (P{p_id})",
            xlabel="Potential",
            ylabel="Current"
        )

        # ✅ CLEAR AFTER USE
        LAST_RESULTS.pop(key, None)

        return send_file(img, mimetype="image/png")

    except Exception:
        LAST_RESULTS.pop(key, None)
        img = error_figure("CV Plot Error", "Potential", "Current")
        return send_file(img, mimetype="image/png")


# -----------------------------------
# LINEAR VOLTAMMETRY (CSV)
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
            LAST_RESULTS.pop((p_id, "lv"), None)
            return jsonify({"error": "Measurement failed"}), 500

        LAST_RESULTS[(p_id, "lv")] = result

        return send_file(io.BytesIO(result),
                         mimetype="text/csv",
                         as_attachment=True,
                         download_name=f"lv_p{p_id}.csv")

    except Exception as e:
        LAST_RESULTS.pop((p_id, "lv"), None)
        return jsonify({"error": str(e)}), 500


# -----------------------------------
# LINEAR VOLTAMMETRY (PLOT)
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/linear_voltammetry/plot", methods=["GET"])
def linear_voltammetry_plot(p_id):
    key = (p_id, "lv")
    try:
        result = LAST_RESULTS.get(key)

        if result is None:
            img = error_figure("No LV Data", "Potential", "Current")
            return send_file(img, mimetype="image/png")

        img = making_figure(
            result,
            title=f"Linear Voltammetry (P{p_id})",
            xlabel="Potential",
            ylabel="Current"
        )

        LAST_RESULTS.pop(key, None)

        return send_file(img, mimetype="image/png")

    except Exception:
        LAST_RESULTS.pop(key, None)
        img = error_figure("LV Plot Error", "Potential", "Current")
        return send_file(img, mimetype="image/png")


# -----------------------------------
# OPEN CIRCUIT (CSV)
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
            LAST_RESULTS.pop((p_id, "ocp"), None)
            return jsonify({"error": "Measurement failed"}), 500

        LAST_RESULTS[(p_id, "ocp")] = result

        return send_file(io.BytesIO(result),
                         mimetype="text/csv",
                         as_attachment=True,
                         download_name=f"ocp_p{p_id}.csv")

    except Exception as e:
        LAST_RESULTS.pop((p_id, "ocp"), None)
        return jsonify({"error": str(e)}), 500


# -----------------------------------
# OPEN CIRCUIT (PLOT)
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/open_circuit/plot", methods=["GET"])
def open_circuit_plot(p_id):
    key = (p_id, "ocp")
    try:
        result = LAST_RESULTS.get(key)

        if result is None:
            img = error_figure("No OCP Data", "Time", "Potential")
            return send_file(img, mimetype="image/png")

        img = making_figure(
            result,
            title=f"Open Circuit Potential (P{p_id})",
            xlabel="Time",
            ylabel="Potential"
        )

        LAST_RESULTS.pop(key, None)

        return send_file(img, mimetype="image/png")

    except Exception:
        LAST_RESULTS.pop(key, None)
        img = error_figure("OCP Plot Error", "Time", "Potential")
        return send_file(img, mimetype="image/png")


# -----------------------------------
# ELECTROLYSIS (CSV)
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
            LAST_RESULTS.pop((p_id, "el"), None)
            return jsonify({"error": "Measurement failed"}), 500

        LAST_RESULTS[(p_id, "el")] = result

        return send_file(io.BytesIO(result),
                         mimetype="text/csv",
                         as_attachment=True,
                         download_name=f"electrolysis_p{p_id}.csv")

    except Exception as e:
        LAST_RESULTS.pop((p_id, "el"), None)
        return jsonify({"error": str(e)}), 500


# -----------------------------------
# ELECTROLYSIS (PLOT)
# -----------------------------------
@potentiostat_bp.route("/<int:p_id>/electrolysis/plot", methods=["GET"])
def electrolysis_plot(p_id):
    key = (p_id, "el")
    try:
        result = LAST_RESULTS.get(key)

        if result is None:
            img = error_figure("No Electrolysis Data", "Time", "Current")
            return send_file(img, mimetype="image/png")

        img = making_figure(
            result,
            title=f"Electrolysis (P{p_id})",
            xlabel="Time",
            ylabel="Current"
        )

        LAST_RESULTS.pop(key, None)

        return send_file(img, mimetype="image/png")

    except Exception:
        LAST_RESULTS.pop(key, None)
        img = error_figure("Electrolysis Plot Error", "Time", "Current")
        return send_file(img, mimetype="image/png")