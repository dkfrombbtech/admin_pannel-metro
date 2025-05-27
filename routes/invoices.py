from flask import Blueprint, request, jsonify
from sqlite3 import IntegrityError
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

# create maininvoice
@invoice_bp.route('/maininvoice', methods=['POST'])
@token_required
def create_main_invoice():
    try:
        data = request.get_json()
        dealer_id = data.get('dealerid')  # Changed here
        date = data.get('date')
        day = data.get('day')

        if not dealer_id or not date or not day:
            return jsonify({"error": "dealerid, date, and day are required"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO main_invoices (dealer_id, date, day)
            VALUES (?, ?, ?)
        """, (dealer_id, date, day))
        
        main_invoice_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "message": "Main invoice created",
            "main_invoice_id": main_invoice_id
        }), 201

    except IntegrityError:
        return jsonify({"error": "Duplicate main invoice for this dealer on the given date and day"}), 409

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# get all main invoices
@invoice_bp.route('/maininvoice', methods=['GET'])
@token_required
def get_main_invoices_by_dealer():
    dealer_id = request.args.get('dealerid')

    if not dealer_id:
        return jsonify({"error": "dealerid is required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM main_invoices
            WHERE dealer_id = ?
        """, (dealer_id,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        conn.close()
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#create subinvoice
@invoice_bp.route('/subinvoice', methods=['POST'])
@token_required
def create_sub_invoice():
    try:
        data = request.get_json()
        required_fields = ['main_invoice_id', 'product_name', 'quantity', 'standard_price']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing one or more required fields: main_invoice_id, product_name, quantity, standard_price"}), 400

        quantity = int(data['quantity'])
        standard_price = int(data['standard_price'])
        total = quantity * standard_price
        main_invoice_id = data['main_invoice_id']

        conn = get_connection()
        cursor = conn.cursor()

        # Insert the new sub-invoice
        cursor.execute("""
            INSERT INTO sub_invoices (main_invoice_id, product_name, quantity, standard_price, total)
            VALUES (?, ?, ?, ?, ?)
        """, (
            main_invoice_id,
            data['product_name'],
            quantity,
            standard_price,
            total
        ))

        # Get the dealer_id for the given main_invoice_id
        cursor.execute("""
            SELECT dealer_id FROM main_invoices WHERE id = ?
        """, (main_invoice_id,))
        dealer_row = cursor.fetchone()

        if dealer_row is None:
            cursor.close()
            conn.close()
            return jsonify({"error": "Main invoice not found"}), 404

        dealer_id = dealer_row[0]

        # Update net_revenue and balance for the dealer
        cursor.execute("""
            UPDATE dealers
            SET net_revenue = net_revenue + ?,
                balance = balance + ?
            WHERE id = ?
        """, (total, total, dealer_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Sub-invoice created and dealer updated successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# get all subinvoice
@invoice_bp.route('/subinvoices/<int:main_invoice_id>', methods=['GET'])
@token_required
def get_sub_invoices(main_invoice_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM sub_invoices
            WHERE main_invoice_id = ?
        """, (main_invoice_id,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        conn.close()

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@invoice_bp.route('/del_subinvoice', methods=['DELETE'])
@token_required
def delete_sub_invoice_direct():
    try:
        data = request.get_json()
        required_fields = ['dealer_id', 'subinvoice_id']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields: dealer_id, subinvoice_id"}), 400

        dealer_id = data['dealer_id']
        subinvoice_id = data['subinvoice_id']

        conn = get_connection()
        cursor = conn.cursor()

        # Get the total from sub_invoices
        cursor.execute("SELECT total FROM sub_invoices WHERE id = ?", (subinvoice_id,))
        row = cursor.fetchone()

        if row is None:
            cursor.close()
            conn.close()
            return jsonify({"error": "Sub-invoice not found"}), 404

        total = row[0]

        # Delete the sub-invoice
        cursor.execute("DELETE FROM sub_invoices WHERE id = ?", (subinvoice_id,))

        # Update dealer's financials
        cursor.execute("""
            UPDATE dealers
            SET net_revenue = net_revenue - ?,
                balance = balance - ?
            WHERE id = ?
        """, (total, total, dealer_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Sub-invoice deleted and dealer updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

