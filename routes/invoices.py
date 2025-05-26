from flask import Blueprint, request, jsonify
from db import get_connection

invoice_bp = Blueprint('invoices', __name__)
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

# 1. Create dealer_invoice_id with provided day
@invoice_bp.route('/maininvoice', methods=['POST'])
@token_required
def create_main_invoice():
    try:
        data = request.get_json()
        dealerid = data.get('dealerid')
        date = data.get('date')
        day = data.get('day')

        if not dealerid or not date or not day:
            return jsonify({"error": "dealerid, date, and day are required"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO dealer_invoice_ids (dealerid, date, day)
            VALUES (?, ?, ?)
        """, (dealerid, date, day))

        dealer_invoice_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Main dealer invoice created", "dealer_invoice_id": dealer_invoice_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. Get all dealer_invoice_ids for a dealer
@invoice_bp.route('/maininvoice', methods=['GET'])
@token_required
def get_main_invoices_by_dealer():
    dealerid = request.args.get('dealerid')

    if not dealerid:
        return jsonify({"error": "dealerid is required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM dealer_invoice_ids
            WHERE dealerid = ?
        """, (dealerid,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        conn.close()
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. Create sub-invoice under dealer_invoice_id
@invoice_bp.route('/subinvoice', methods=['POST'])
@token_required
def create_sub_invoice():
    try:
        data = request.get_json()
        required_fields = ['dealer_invoice_id', 'product_name', 'quantity', 'standard_price']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing one or more required fields"}), 400

        quantity = int(data['quantity'])
        standard_price = int(data['standard_price'])
        total = quantity * standard_price

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO dealer_invoices (dealer_invoice_id, product_name, quantity, standard_price, total)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data['dealer_invoice_id'],
            data['product_name'],
            quantity,
            standard_price,
            total
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Sub-invoice created successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. Get all sub-invoices for a dealer_invoice_id
@invoice_bp.route('/subinvoices/<int:dealer_invoice_id>', methods=['GET'])
@token_required
def get_sub_invoices(dealer_invoice_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM dealer_invoices
            WHERE dealer_invoice_id = ?
        """, (dealer_invoice_id,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        conn.close()

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 5. Delete sub-invoices based on invoice id
@invoice_bp.route('/subinvoices/<int:invoice_id>', methods=['DELETE'])
@token_required
def delete_sub_invoice(invoice_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get the total and dealer_invoice_id and dealerid before deletion
        cursor.execute("""
            SELECT total, dealer_invoice_id FROM dealer_invoices WHERE id = ?
        """, (invoice_id,))
        invoice = cursor.fetchone()

        if not invoice:
            return jsonify({"error": "Sub-invoice not found"}), 404

        total, dealer_invoice_id = invoice

        # Get the dealerid from dealer_invoice_ids table using dealer_invoice_id
        cursor.execute("""
            SELECT dealerid FROM dealer_invoice_ids WHERE id = ?
        """, (dealer_invoice_id,))
        dealer = cursor.fetchone()

        if not dealer:
            return jsonify({"error": "Dealer not found for this invoice"}), 404

        dealerid = dealer[0]

        # Delete the sub-invoice
        cursor.execute("DELETE FROM dealer_invoices WHERE id = ?", (invoice_id,))

        # Subtract total from dealer's net_revenue and balance
        cursor.execute("""
            UPDATE dealers
            SET net_revenue = net_revenue - ?,
                balance = balance - ?
            WHERE id = ?
        """, (total, total, dealerid))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Sub-invoice deleted and dealer totals updated"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
