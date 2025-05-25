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

# create an invoice
@invoice_bp.route('/create', methods=['POST'])
@token_required
def create_invoice():
    try:
        data = request.get_json()
        required_fields = ['dealerid', 'product_name', 'quantity', 'standard_price', 'date']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing one or more required fields"}), 400

        quantity = int(data['quantity'])
        standard_price = int(data['standard_price'])
        total = quantity * standard_price
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dealer_invoices (dealerid, product_name, quantity, standard_price, date, total)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data['dealerid'],
            data['product_name'],
            quantity,
            standard_price,
            data['date'],
            total
        ))
        cursor.execute("""
            UPDATE dealers
            SET net_revenue = COALESCE(net_revenue, 0) + ?,
                balance = COALESCE(balance, 0) + ?
            WHERE id = ?
        """, (total, total, data['dealerid']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Invoice created and dealer totals updated"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# get inovices per date and dealer
@invoice_bp.route('/filter', methods=['GET'])
@token_required
def get_invoices_by_dealer_and_date():
    dealer_id = request.args.get('dealerid')
    date = request.args.get('date')

    if not dealer_id:
        return jsonify({"error": "dealerid is required"}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()

        if date:
            cursor.execute("""
                SELECT * FROM dealer_invoices
                WHERE dealerid = ? AND date = ?
            """, (dealer_id, date))
        else:
            cursor.execute("""
                SELECT * FROM dealer_invoices
                WHERE dealerid = ?
            """, (dealer_id,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
        cursor.close()
        conn.close()
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Delete an invoice
@invoice_bp.route('/<int:invoice_id>', methods=['DELETE'])
@token_required
def delete_invoice(invoice_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT dealerid, total FROM dealer_invoices WHERE id = ?", (invoice_id,))
        invoice = cursor.fetchone()

        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404

        dealerid, total = invoice
        cursor.execute("DELETE FROM dealer_invoices WHERE id = ?", (invoice_id,))

        cursor.execute("""
            UPDATE dealers
            SET net_revenue = net_revenue - ?,
                balance = balance - ?
            WHERE id = ?
        """, (total, total, dealerid))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Invoice deleted and dealer totals updated"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500