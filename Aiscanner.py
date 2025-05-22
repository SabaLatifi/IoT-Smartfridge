import cv2
import time
import requests
from pyzbar import pyzbar
from picamera2 import Picamera2
from ultralytics import YOLO

# ----------- Nutrition Lookup ----------
def lookup_product(barcode):
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 1:
                product = data["product"]
                return {
                    "product_name": product.get("product_name", "Unknown Product"),
                    "calories": product.get("nutriments", {}).get("energy-kcal_100g", "N/A"),
                    "protein": product.get("nutriments", {}).get("proteins_100g", "N/A"),
                    "sugar": product.get("nutriments", {}).get("sugars_100g", "N/A"),
                    "carbs": product.get("nutriments", {}).get("carbohydrates_100g", "N/A"),
                    "fat": product.get("nutriments", {}).get("fat_100g", "N/A")
                }
            else:
                print(f"Product not found for barcode: {barcode}")
                return None
        else:
            print(f"API error with status code {response.status_code} for barcode: {barcode}")
            return None
    except Exception as e:
        print(f"Error during API request for barcode {barcode}: {str(e)}")
        return None

# ----------- API Sender ----------
def send_to_api(data):
    try:
        response = requests.post("http://127.0.0.1:5000/scan", json=data, timeout=5)
        if response.status_code == 200:
            print("✅ Sent to API")
        else:
            print(f"⚠️ API error: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to send to API: {str(e)}")

# ----------- Camera Setup ----------
picam2 = Picamera2()
picam2.preview_configuration.main.size = (480, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.align()
picam2.configure("preview")
picam2.start()

time.sleep(2)
picam2.set_controls({"AfMode": 1})
time.sleep(1)
picam2.set_controls({"AfTrigger": 0})
time.sleep(2)

# ----------- YOLO Model ----------
model = YOLO("yolov8n_ncnn_model")  # Adjust path as needed

# ----------- Main Loop ----------
scanned_barcodes = {}
frame_count = 0

print("Scanner running... Press 'q' to exit.")

while True:
    # Capture frame from the camera
    frame = picam2.capture_array()

    # Optional: Run YOLO object detection (not shown on frame)
    _ = model.predict(frame, imgsz=320)

    # Decode the barcodes
    barcodes = pyzbar.decode(frame)
    for barcode in barcodes:
        try:
            x, y, w, h = barcode.rect
            barcode_data = barcode.data.decode("utf-8")
            barcode_type = barcode.type

            # Check if barcode has been scanned before
            if barcode_data not in scanned_barcodes:
                # Lookup the product information
                nutrition = lookup_product(barcode_data)

                # Only send to API if the lookup was successful (nutrition data is valid)
                if nutrition is not None:
                    nutrition["barcode"] = barcode_data
                    scanned_barcodes[barcode_data] = nutrition

                    # Send valid data to the API
                    send_to_api(nutrition)
                    print(f"Scanned: {barcode_type} ({barcode_data}): {nutrition}")
                else:
                    print(f"Skipping invalid product: {barcode_data}")
            else:
                nutrition = scanned_barcodes[barcode_data]

            # Draw bounding box around barcode
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Display product name above barcode
            product_text = f"{nutrition.get('product_name', '')} ({barcode_data})"
            cv2.putText(frame, product_text, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Draw nutrition panel
            panel_x = x
            panel_y = y + h + 10
            spacing = 20
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            color = (255, 255, 255)

            nutrition_info = [
                f"Calories: {nutrition.get('calories', 'N/A')} kcal",
                f"Protein: {nutrition.get('protein', 'N/A')} g",
                f"Sugar: {nutrition.get('sugar', 'N/A')} g",
                f"Carbs: {nutrition.get('carbs', 'N/A')} g",
                f"Fat: {nutrition.get('fat', 'N/A')} g"
            ]

            # Draw a semi-transparent background
            overlay = frame.copy()
            cv2.rectangle(overlay, (panel_x, panel_y),
                          (panel_x + 220, panel_y + spacing * len(nutrition_info) + 10),
                          (0, 0, 0), -1)
            alpha = 0.5
            frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

            # Draw nutrition text
            for i, line in enumerate(nutrition_info):
                cv2.putText(frame, line, (panel_x + 5, panel_y + (i + 1) * spacing),
                            font, font_scale, color, 1)

        except Exception as e:
            print(f"Error processing barcode: {e}")

    # Re-focus every 30 frames
    frame_count += 1
    if frame_count % 30 == 0:
        picam2.set_controls({"AfTrigger": 0})
        time.sleep(0.2)

    # Display the frame
    cv2.imshow("Product Nutrition Scanner", frame)

    # Exit the program if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
