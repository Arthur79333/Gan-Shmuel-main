import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import pandas as pd

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

db_connection = None


def check_db_connection():
    try:
        db_connection.execute(text("select 1"))
        return True
    except OperationalError as e:
        print("OperationalError:", e)
        return jsonify({"status": "Failure"}), 500


@app.route('/health', methods=['GET'])
def health_check():
    if check_db_connection():
        return jsonify({"status": "OK"}), 200
    else:
        return jsonify({"status": "Failure"}), 500


@app.route('/session/<int:session_id>', methods=['GET'])
def get_session(session_id):
    try:
        result = db_connection.execute(text("SELECT * FROM transactions WHERE id = :id"), {"id": session_id})
        session_row = result.fetchone()

        if not session_row:
            return jsonify({"error": "Session not found"}), 404

        session_data = {
            "id": str(session_row[0]),
            "truck": session_row[3] if session_row[3] else "na",
            "bruto": int(session_row[5]) if session_row[5] is not None else 0
        }

        if session_row[2].upper() == "OUT":
            session_data["truckTara"] = int(session_row[6]) if session_row[6] is not None else 0
            if session_row[7] is None:
                session_data["neto"] = "na"
            else:
                session_data["neto"] = int(session_row[7])

        return jsonify(session_data), 200

    except Exception as e:
        print(f"Exception occurred in 'get_session': {e}")
        return jsonify({"error": "Internal server error: {}".format(str(e))}), 500


@app.route('/weight', methods=['POST'])
def weights():
    try:
        direction = request.json.get('direction')
        truck = request.json.get('truck')
        containers = request.json.get('containers')
        weight = request.json.get('weight')
        unit = request.json.get('unit')
        force = request.json.get('force', False)
        produce = request.json.get('produce')

        if unit == 'lbs':
            weight = weight * 0.453592

        with open("in/trucks.json", "r") as f:
            trucks_data = json.load(f)

        truck_weight_kg = next((truck_data["weight"] for truck_data in trucks_data if truck_data["id"] == truck), 0) * 0.453592

        result = db_connection.execute(
            text("SELECT id, direction FROM transactions WHERE truck = :truck ORDER BY datetime DESC LIMIT 1"),
            {"truck": truck})
        rows = list(result.fetchall())
        last_entry = rows[0] if rows else None

        if last_entry:
            last_id, last_direction = last_entry[0], last_entry[1]
        else:
            last_direction = None

        if direction.lower() == 'in':
            if last_direction == 'in':
                if force:
                    db_connection.execute(text(
                        "UPDATE transactions SET datetime=:datetime, containers=:containers, bruto=:bruto, produce=:produce WHERE id=:id"),
                                          {"datetime": datetime.now(), "containers": containers, "bruto": weight,
                                           "produce": produce, "id": last_id})
                    return jsonify({"id": last_id, "truck": truck, "bruto": weight}), 201
                else:
                    return jsonify({"error": "Consecutive 'in' records not allowed. Use force to override."}), 400
            else:
                result = db_connection.execute(text(
                    "INSERT INTO transactions (datetime, direction, truck, containers, bruto, produce) VALUES (:datetime, :direction, :truck, :containers, :bruto, :produce)"),
                                               {"datetime": datetime.now(), "direction": direction, "truck": truck,
                                                "containers": containers, "bruto": weight, "produce": produce})
                return jsonify({"id": result.lastrowid, "truck": truck, "bruto": weight}), 201

        elif direction.lower() == 'out':
            result = db_connection.execute(text(
                "SELECT bruto FROM transactions WHERE truck = :truck AND direction = 'in' ORDER BY datetime DESC LIMIT 1"),
                {"truck": truck})
            bruto_record = result.fetchone()

            if not bruto_record:
                return jsonify({"error": "No 'in' record found for the truck."}), 400

            bruto = bruto_record[0]

            if bruto is None:
                return jsonify({"error": "Invalid 'bruto' value for the truck's 'in' record."}), 400

            neto = bruto - weight
            total_container_weight = 0

            for container in containers.split(','):
                result = db_connection.execute(
                    text("SELECT weight FROM containers_registered WHERE container_id = :container_id"),
                    {"container_id": container.strip()})
                container_weight = result.fetchone()

                if not container_weight:
                    neto = "na"
                    break
                else:
                    total_container_weight += container_weight[0]

            if neto != "na":
                neto -= (truck_weight_kg + total_container_weight)

                if neto < 0:
                    neto = 0
            result = db_connection.execute(text(
                "INSERT INTO transactions (datetime, direction, truck, containers, bruto, truckTara, neto, produce) VALUES (:datetime, :direction, :truck, :containers, :bruto, :weight, :neto, :produce)"),
                                           {"datetime": datetime.now(), "direction": direction, "truck": truck,
                                            "containers": containers, "bruto": bruto, "weight": weight,
                                            "neto": (neto if neto != "na" else None), "produce": produce})
            return jsonify({"id": result.lastrowid, "truck": truck, "bruto": weight, "truckTara": truck_weight_kg, "neto": neto}), 201

        elif direction.lower() == 'none':
            if last_direction == 'in':
                return jsonify({"error": "'none' direction cannot follow 'in' direction."}), 400

            result = db_connection.execute(text(
                "INSERT INTO transactions (datetime, direction, truck, containers, bruto, produce) VALUES (:datetime, :direction, :truck, :containers, :bruto, :produce)"),
                                           {"datetime": datetime.now(), "direction": direction, "truck": truck,
                                            "containers": containers, "bruto": weight, "produce": produce})
            return jsonify({"id": result.lastrowid, "truck": truck, "bruto": weight}), 201

        else:
            return jsonify({"error": "Invalid direction value."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/unknown', methods=['GET'])
def get_unknown_containers():
    try:
        result = db_connection.execute(
            text("SELECT container_id FROM containers_registered WHERE weight IS NULL")).fetchall()

        if not result:
            return jsonify([]), 200

        unknown_containers = [str(row[0]) for row in result]

        return jsonify(unknown_containers), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/item/<item_id>', methods=['GET'])
def get_item_info(item_id):
    try:
        t1 = request.args.get('from', datetime.now().replace(day=1).strftime('%Y%m%d%H%M%S'))
        t2 = request.args.get('to', datetime.now().strftime('%Y%m%d%H%M%S'))

        result = db_connection.execute(
            text("SELECT * FROM transactions WHERE truck = :truck AND datetime BETWEEN :t1 AND :t2"),
            {"truck": item_id, "t1": t1, "t2": t2})
        rows = result.fetchall()

        if rows:
            last_known_tara = rows[-1][6] if rows[-1][6] is not None else "na"
            sessions = [row[0] for row in rows]
            return jsonify({"id": item_id, "tara": last_known_tara, "sessions": sessions}), 200

        result = db_connection.execute(
            text("SELECT * FROM transactions WHERE id = :id AND datetime BETWEEN :t1 AND :t2"),
            {"id": item_id, "t1": t1, "t2": t2})
        rows = result.fetchall()

        if rows:
            last_known_tara = rows[-1][6] if rows[-1][6] is not None else "na"
            sessions = [row[0] for row in rows]
            return jsonify({"id": item_id, "tara": last_known_tara, "sessions": sessions}), 200

        result = db_connection.execute(text("SELECT * FROM containers_registered WHERE container_id = :id"),
                                       {"id": item_id})
        container_row = result.fetchone()

        if not container_row:
            return jsonify({"error": "Item not found"}), 404

        return jsonify({"id": container_row[0], "tara": container_row[1], "sessions": []}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/weight', methods=['GET'])
def get_weight_records():
    if 'from' in request.args:
        t1 = request.args['from']
    else:
        t1 = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d000000')

    if 'to' in request.args:
        t2 = request.args['to']
    else:
        t2 = datetime.now().strftime('%Y%m%d%H%M%S')

    filter_criteria = request.args.get('filter', "in,out,none")

    try:
        query = text(
            "SELECT * FROM transactions WHERE datetime BETWEEN :t1 AND :t2 AND direction IN :filter_criteria"
        )

        result = db_connection.execute(query,
                                       {'t1': t1, 't2': t2, 'filter_criteria': tuple(filter_criteria.split(','))})

        weight_records = [{
            "id": record[0],
            "direction": record[2],
            "bruto": record[5],
            "neto": (max(record[7], 0) if record[7] is not None else "na"),
            "produce": record[8],
            "containers": record[4].split(',')
        } for record in result]

        if not weight_records:
            return jsonify({"error": "No weight records found for the given parameters"}), 404

        return jsonify(weight_records), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/batch-weight', methods=['POST'])
def upload_weights_from_file():
    try:
        file = request.files.get('file')

        if not file:
            return jsonify({"error": "No file provided"}), 400

        file_path = os.path.join('in', file.filename)
        file.save(file_path)

        file_ext = os.path.splitext(file_path)[-1].lower()

        if file_ext == '.csv':
            process_weights_from_file(file_path)
            return jsonify({"status": "success", "message": "Weights uploaded and processed successfully"}), 201

        elif file_ext == '.json':
            return jsonify({"status": "success", "message": "File saved successfully"}), 201

        else:
            return jsonify({"error": "Unsupported file format"}), 400

    except Exception as e:
        print("Failed to upload weights with error:", e)
        return jsonify({"error": "Failed to upload weights"}), 500
    finally:
        if os.path.exists(file_path) and file_ext == '.csv':
            os.remove(file_path)

def process_weights_from_file(file_path):
    weights_df = pd.read_csv(file_path)
    if "lbs" in weights_df.columns:
        weights_df['kg'] = weights_df['lbs'] * 0.453592  # Convert lbs to kg
        for _, row in weights_df.iterrows():
            save_weight_to_db(row['id'], row['kg'], 'kg')
    else:
        for _, row in weights_df.iterrows():
            save_weight_to_db(row['id'], row['kg'], 'kg')

def save_weight_to_db(container_id, weight, unit):
    try:
        db_connection.execute(text("""
            INSERT INTO containers_registered (container_id, weight, unit)
            VALUES (:container_id, :weight, :unit)
        """), {
            'container_id': container_id,
            'weight': weight,
            'unit': unit
        })
        db_connection.commit()
    except Exception as e:
        print("Failed to update weights with error:", e)

def main():
    global db_connection

    try:
        engine = create_engine(DATABASE_URL)
        db_connection = engine.connect()
    except OperationalError as e:
        print("failed to connect to db with error: ", e)
        exit(1)

    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    main()
