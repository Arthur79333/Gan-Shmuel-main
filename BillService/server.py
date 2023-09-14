import os
from flask import Flask, jsonify ,request, send_file
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
import pandas as pd
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

# Define the database URL

DATABASE_URL = os.environ.get('DATABASE_URL')

db_connection = None


# Function to check database connection
def check_db_connection():
    try:
        db_connection.execute(text("select 1;"))
        return True
    except OperationalError as e:
        print("OperationalError:", e)
        return False
    finally:
        db_connection.rollback()
    

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    if check_db_connection() and db_connection is not None:
        return jsonify({"status": "OK"}), 200
    else:
        return jsonify({"status": "Failure"}), 500


@app.route('/truck/<truck_id>', methods=['PUT'])
def update_provider_id(truck_id): 
    new_provider_id = request.json.get('new_provider_id')
    if not new_provider_id :
        return jsonify({"error": "Provider ID is required"}), 400 
     
    try:
        result = db_connection.execute(text("UPDATE Trucks SET provider_id =:provider_id WHERE id =:id"),{
            'id': truck_id,
            'provider_id': new_provider_id
        })
        if result.rowcount == 0:
            return jsonify({"error":"Truck ID not found"}),404
        db_connection.commit()
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        print("Failed to update provider id with error:", e)
        return jsonify({"status": "Failure"}), 500
    


@app.route("/provider/<int:provider_id>", methods=["PUT"])
def update_provider(provider_id):
    provider_new_name = request.json.get('name')
    id = db_connection.execute(text("SELECT id FROM Provider WHERE id = :provider_id"),{
        'provider_id':provider_id
    }).fetchone()

    if provider_new_name is None:
        return jsonify({"error": "No Provider name is provided"}), 400
    if not id:
        return jsonify({"error": "Provider id is required"}), 400
    try:
        db_connection.execute(text("UPDATE Provider SET name =:name WHERE id= :id"),{
            'id':provider_id,
            'name':provider_new_name,
        })  
        db_connection.commit()
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        print("Failed to update provider name with error: ", e)
        return jsonify({"status": "Failure"}), 500


@app.route("/provider", methods=["POST"])
def create_provider():
    provider_name = request.json.get('provider_name')

    if not provider_name:
        return jsonify({"error": "provider name is required"}), 400

    try:
        result = db_connection.execute(text("INSERT INTO Provider (name) VALUES (:name)"), {'name': provider_name},)
        db_connection.commit()    
        id =result.lastrowid  
        return jsonify({'id': id}),201  
    except Exception as e:
        print("failed to add provider name with error: ", e)
        return jsonify({"error": "Faild to add new provider name."}), 500


@app.route('/truck', methods=['POST'])
def add_truck_id():
    id = request.json.get('id')
    provider_id = request.json.get('provider_id')

    # Check if truck ID was provided
    if not id:
        return jsonify({"error": "Truck ID is required"}), 400

    try:
        db_connection.execute(text("INSERT INTO Trucks (id, provider_id) VALUES (:id, :provider_id)"), {
            'id': id,
            'provider_id': provider_id
        })
        db_connection.commit()
        return jsonify({"status": "success", "message": "Truck added!"}), 201
    except Exception as e:
        print("failed to add truck with error: ", e)
        return jsonify({"error": "Truck with this ID already exists or the provided provider_id doesn't match any existing providers."}), 400



@app.route('/truck/<truck_id>',methods=['GET'])
def get_truck_weight(truck_id):
    t1_str = request.args.get('from', datetime.now().replace(day=1).strftime('%Y%m%d%H%M%S'))
    t2_str = request.args.get('to', datetime.now().strftime('%Y%m%d%H%M%S'))

    t1 = datetime.strptime(t1_str, '%Y%m%d%H%M%S')
    t2 = datetime.strptime(t2_str, '%Y%m%d%H%M%S')
    weight_api = f"http://51.17.41.172:8081/item/{truck_id}?from={t1}&to={t2}"
    params = {

        "id": "id",
        "sessions": "sessions",
        "tara":  "tara"

    }
    try:
        response = requests.get(weight_api, params=params)
        return response.json(), 200
    except:
        return jsonify({"error": "invalid truck id"}), 400


# > Reminder: `Bruto = Neto (fruit) + Tara (truck) + sum(Tara (containers))`


@app.route('/bill/<id>', methods=['GET'])
def get_bill(id):
    t1 = request.args.get('from', datetime.now().replace(day=1).strftime('%Y%m%d%H%M%S'))
    t2 = request.args.get('to', datetime.now().strftime('%Y%m%d%H%M%S'))
    f = 'out'

    # Fetch provider name from the Provider table
    provider_name = db_connection.execute(text("SELECT name FROM Provider WHERE id = :id"), {'id': id}).fetchone()

    if not provider_name:
        return jsonify({"error": "Provider not found"}), 404

    provider_name = provider_name[0]

    # Fetch truck IDs associated with the given provider
    truck_ids = db_connection.execute(text("SELECT id FROM Trucks WHERE provider_id = :id"), {'id': id}).fetchall()
    truck_ids = [truck_id[0] for truck_id in truck_ids]

    # Fetch weight sessions data from the weight service for each truck
    total_amount = 0
    total_pay = 0
    products = []

    t1_formatted = datetime.strptime(t1, '%Y%m%d%H%M%S').strftime('%d/%m/%Y %H:%M:%S')
    t2_formatted = datetime.strptime(t2, '%Y%m%d%H%M%S').strftime('%d/%m/%Y %H:%M:%S')

    for truck_id in truck_ids:
        # Get weight records from the /weight API
        session_api = f"http://51.17.41.172:8081/weight?from={t1}&to={t2}&filter={f}"
        session_response = requests.get(session_api)

        if session_response.status_code == 200:
            session_data = session_response.json()
            for session_record in session_data:
                product = session_record.get("produce")
                neto = session_record.get("neto")

                if neto == 'na':
                    print("Skipping record with 'na' neto value")
                    continue

                # Fetch the rate based on the product and provider_id (scope)
                rate_query = text("""
                    SELECT rate FROM Rates
                    WHERE product_id = :product AND (scope = 'All' OR scope = :provider_id)
                """)
                rate_result = db_connection.execute(rate_query, {
                    'product': product,
                    'provider_id': id
                }).fetchone()

                if rate_result is not None:
                    rate = rate_result[0]
                    pay = float(neto) * float(rate)
                    total_amount += float(neto)
                    total_pay += pay

                    # Update the products list
                    products.append({
                        "product": product,
                        "count": 1,
                        "amount": float(neto),
                        "rate": float(rate),
                        "pay": pay
                    })
                else:
                    print(f"Failed to fetch rate data for product {product}")

        else:
            print(f"Failed to fetch session data for truck {truck_id}")

    bill = {
        "id": id,
        "name": provider_name,
        "from": t1_formatted,
        "to": t2_formatted,
        "truckCount": len(truck_ids),
        "products": products,
        "total": total_pay
    }

    return jsonify(bill), 200


@app.route('/rates', methods=['POST'])
def upload_rates_from_excel():
    try:
        file = request.files.get('file')

        if not file:
            return jsonify({"error": "No file provided"}), 400

        # Save the uploaded Excel file
        file_path = os.path.join('in', file.filename)
        file.save(file_path)

        # Process and save the rates from the Excel file
        process_rates_from_excel(file_path)

        return jsonify({"status": "success", "message": "Rates uploaded successfully"}), 201
    except Exception as e:
        print("Failed to upload rates with error:", e)
        return jsonify({"error": "Failed to upload rates"}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# Function to process rates from Excel file
def process_rates_from_excel(file_path):
    rates_df = pd.read_excel(file_path)

    # Clear old rates before updating with new rates
    db_connection.execute(text("DELETE FROM Rates"))
    db_connection.commit()

    # Process and save the rates to the database
    for _, row in rates_df.iterrows():
        product_id = row['Product']
        rate = row['Rate']
        scope = row['Scope']
        # provider_id = row.get('Provider', None)  # Assuming 'Provider' column in the Excel

        # Handle scope-based rate or 'ALL' rate
        # if scope == 'ALL':
        #     provider_id = None

        # Insert rate into the database
        try:
            db_connection.execute(text("""
                INSERT INTO Rates (product_id, rate, scope)
                VALUES (:product_id, :rate, :scope)
            """), {
                'product_id': product_id,
                'rate': rate,
                'scope': scope
            })
            db_connection.commit()
        except Exception as e:
            print("Failed to update rates with error:", e)




@app.route('/rates', methods=['GET'])
def download_rates_as_excel():
    try:
        # Fetch rates from the database
        rates_df = pd.read_sql("SELECT r.product_id, r.rate, p.name AS scope FROM Rates r LEFT JOIN Provider p ON r.scope = p.id", db_connection)
        
        excel_path = 'in/rates.xlsx'
        rates_df.to_excel(excel_path, index=False)

        return send_file(excel_path, as_attachment=True), 200
    except Exception as e:
        print("Failed to download rates with error:", e)
        return jsonify({"error": "Failed to download rates"}), 500
    finally:
        if os.path.exists(excel_path):
            os.remove(excel_path)




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
