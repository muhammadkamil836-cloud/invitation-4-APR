import pandas as pd
import requests
from flask import Flask, request, render_template_string
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# SS Credentials
USERNAME = "960553"
PASSWORD = "13658f5b-c38b-4c40-b1a2-8a28c3262e70"

# Required CSV Columns
REQUIRED_COLUMNS = [
    "CustomerPO",
    "Identifier",
    "Qty",
    "Attn",
    "Address",
    "City",
    "State",
    "Zip",
    "ShippingMethod",
    "shipBlind",
    "PaymentProfile-Email",
    "PaymentProfileID"
]

# -------------------------------
# HTML Upload Page
# -------------------------------
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>SS Orders Upload</title>
    <style>
        body { font-family: Arial; background: #f3f3f3; padding: 40px; }
        .box { background: white; padding: 25px; border-radius: 10px; width: 450px; margin: auto; 
               box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; 
               border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .result { margin-top: 20px; padding: 15px; background: #fff; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>SS Activewear Order Upload</h2>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <input type="file" name="file" required><br><br>
            <button class="btn">Upload CSV</button>
        </form>
    </div>

    {% if result %}
    <div class="box result">
        <h3>Result:</h3>
        {{ result|safe }}
    </div>
    {% endif %}
</body>
</html>
"""

# -------------------------------
# Load CSV (supports comma + tab)
# -------------------------------
def load_csv(file_path):
    try:
        return pd.read_csv(file_path, sep=",")
    except:
        return pd.read_csv(file_path, sep="\t")

# -------------------------------
# Home Page
# -------------------------------
@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

# -------------------------------
# Upload Endpoint
# -------------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return render_template_string(HTML_PAGE, result="❌ No file uploaded")

    file = request.files["file"]
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    df = load_csv(path)
    df.columns = [col.strip() for col in df.columns]

    # Validate Columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return render_template_string(
            HTML_PAGE,
            result=f"❌ CSV missing required column(s): {', '.join(missing)}"
        )

    result_messages = []

    # -------------------------------
    # Process Each Order
    # -------------------------------
    for _, row in df.iterrows():
        try:
            po = str(row["CustomerPO"]).strip()

            payload = {
                "shippingAddress": {
                    "customer": row["Attn"],
                    "attn": row["Attn"],
                    "address": row["Address"],
                    "city": row["City"],
                    "state": row["State"],
                    "zip": str(row["Zip"]),
                    "residential": True
                },
                "shippingMethod": str(row["ShippingMethod"]),
                "shipBlind": str(row["shipBlind"]).lower() in ["yes", "1", "true"],
                "poNumber": po,
                "emailConfirmation": row["PaymentProfile-Email"],
                "testOrder": False,

                "paymentProfile": {
                    "email": row["PaymentProfile-Email"],
                    "profileID": int(row["PaymentProfileID"])
                },

                "autoselectWarehouse": True,

                "lines": [
                    {
                        "identifier": row["Identifier"],
                        "qty": int(row["Qty"])
                    }
                ]
            }

            # -------------------------------
            # POST Order to SS
            # -------------------------------
            response = requests.post(
                "https://api.ssactivewear.com/v2/orders",
                json=payload,
                auth=(USERNAME, PASSWORD)
            )

            if response.status_code == 200:
                result_messages.append(f"✔ PO {po} submitted successfully.")
            else:
                result_messages.append(
                    f"<b>❌ PO {po} FAILED — HTTP {response.status_code}</b><br>{response.text}"
                )

        except Exception as e:
            result_messages.append(f"❌ Error processing PO {po}: {str(e)}")

    return render_template_string(
        HTML_PAGE,
        result="<br>".join(result_messages)
    )

if __name__ == "__main__":
    app.run(debug=True)
