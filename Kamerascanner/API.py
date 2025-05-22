from flask import Flask, request, jsonify
from datetime import datetime
import csv
import os

app = Flask(__name__)

# Optional: store scanned data in memory
scanned_products = []

# Optional: CSV logging
CSV_FILE = "scanned_log.csv"
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "barcode", "product_name", "calories", "protein", "sugar", "carbs", "fat"])

@app.route("/scan", methods=["POST"])
def scan():
    data = request.json
    print("✅ Received data:", data)

    # Save to memory
    scanned_products.append(data)

    # Save to CSV
    with open(CSV_FILE, "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            data.get("barcode"),
            data.get("product_name"),
            data.get("calories"),
            data.get("protein"),
            data.get("sugar"),
            data.get("carbs"),
            data.get("fat")
        ])

    return jsonify({"message": "Product saved successfully."}), 200

@app.route("/scans", methods=["GET"])
def get_scans():
    return jsonify(scanned_products)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
