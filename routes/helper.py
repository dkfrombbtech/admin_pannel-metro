from flask import Blueprint, jsonify, request
from num2words import num2words

helper_bp = Blueprint('helper', __name__)

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

@helper_bp.route('/convert', methods=['POST'])
def convert_number():
    data = request.get_json()
    if not data or 'number' not in data:
        return jsonify({"error": "Missing 'number' field"}), 400

    try:
        number = data['number']
        words = num2words(number)
        return jsonify({"words": words})
    except Exception as e:
        return jsonify({"error": str(e)}), 500