from flask import Blueprint, jsonify, request
from db import get_connection

dealer_bp = Blueprint('dealers', __name__)

API_TOKEN = "9f3a7c1d2b4e8f0a"  

def token_required(f):
    def wrapper(*args, **kwargs):
        if request.method == 'OPTIONS':
            return '', 200 

        auth_header = request.headers.get('Authorization', None)
        if auth_header is None or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authorization header missing or malformed"}), 401

        token = auth_header.split(" ")[1]
        if token != API_TOKEN:
            return jsonify({"error": "Invalid or missing token"}), 401

        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# get dealers
@dealer_bp.route('/', methods=['GET', 'OPTIONS'])
@token_required
def get_dealers():
    if request.method == 'OPTIONS':
        return '', 200  

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dealers")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
        cursor.close()
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# create dealer
@dealer_bp.route('/create', methods=['POST'])
@token_required
def create_dealer():
    try:
        data = request.get_json()
        required_fields = ['name', 'contact_person', 'phone_number', 'address', 'city', 'pincode']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing one or more required fields"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dealers (name, contact_person, phone_number, address, city, pincode)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data['name'],
            data['contact_person'],
            data['phone_number'],
            data['address'],
            data['city'],
            data['pincode']
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Dealer created successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# update dealer
@dealer_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_dealer_by_id(id):
    try:
        data = request.get_json()
        required_fields = ['name', 'contact_person', 'phone_number', 'address', 'city', 'pincode']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing one or more required fields"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dealers
            SET name = ?, contact_person = ?, phone_number = ?, address = ?, city = ?, pincode = ?
            WHERE id = ?
        """, (
            data['name'],
            data['contact_person'],
            data['phone_number'],
            data['address'],
            data['city'],
            data['pincode'],
            id
        ))

        if cursor.rowcount == 0:
            return jsonify({"error": "Dealer not found"}), 404

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Dealer updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#dealer details
@dealer_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_dealer_by_id(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dealers WHERE id = ?", (id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Dealer not found"}), 404

        columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))
        cursor.close()
        conn.close()
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# serch Dealer
@dealer_bp.route('/search', methods=['GET'])
@token_required
def search_dealers():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM dealers
            WHERE LOWER(name) LIKE LOWER(?)
        """, (f'{query}%',))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
        cursor.close()
        conn.close()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# balance & revenue
@dealer_bp.route('/<int:id>/stats', methods=['GET'])
@token_required
def get_dealer_stats(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT net_revenue, balance FROM dealers WHERE id = ?
        """, (id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Dealer not found"}), 404

        data = {
            "net_revenue": row[0],
            "balance": row[1]
        }

        cursor.close()
        conn.close()
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Update Balance
@dealer_bp.route('/<int:id>/payment', methods=['POST'])
@token_required
def make_payment(id):
    try:
        data = request.get_json()
        if 'amount' not in data:
            return jsonify({"error": "Missing 'amount' in request body"}), 400

        payment_amount = data['amount']
        if payment_amount <= 0:
            return jsonify({"error": "Payment amount must be greater than zero"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dealers
            SET balance = balance - ?
            WHERE id = ?
        """, (payment_amount, id))

        if cursor.rowcount == 0:
            return jsonify({"error": "Dealer not found"}), 404

        cursor.execute("SELECT balance FROM dealers WHERE id = ?", (id,))
        updated_balance = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Payment applied successfully",
            "updated_balance": updated_balance
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
