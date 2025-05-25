from flask import Flask
from flask_cors import CORS
from routes.dealers import dealer_bp
from routes.invoices import invoice_bp
from routes.helper import helper_bp
import os

app = Flask(__name__)
CORS(app)

app.register_blueprint(dealer_bp, url_prefix='/dealers')
app.register_blueprint(invoice_bp, url_prefix='/invoices')
app.register_blueprint(helper_bp,url_prefix='/helper')

@app.route("/")
def home():
    return "MetroBilling Flask App is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)