from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import uuid
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for front-end communication

# Configure your OCR and Translation API URLs
OCR_UPLOAD_URL = "https://da5a-2401-4900-3ea3-7fa5-7824-53fd-7031-944.ngrok-free.app/api/v1/upload"
OCR_INFERENCE_URL = "https://da5a-2401-4900-3ea3-7fa5-7824-53fd-7031-944.ngrok-free.app/api/v1/inference"
TRANSLATION_API_URL = " https://bumpy-pears-relate.loca.lt/translate"  # Corrected path

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route('/process-image', methods=['POST'])
def process_image():
    try:
        # Get base64 image from the front-end
        data = request.get_json()
        image_data = data.get('image')
        if not image_data:
            return jsonify({'error': 'No image provided'}), 400

        # Decode base64 and save locally
        image_bytes = base64.b64decode(image_data.split(",")[1])
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(image_bytes)

        # Step 1: Upload image to OCR API
        with open(filepath, 'rb') as img_file:
            upload_resp = requests.post(OCR_UPLOAD_URL, files={'file': img_file})

        if upload_resp.status_code != 200:
            return jsonify({'error': 'OCR upload failed', 'details': upload_resp.text}), 500

        image_id = upload_resp.json()['data']['ids'][0]

        # Step 2: Run OCR inference
        payload = [{
            "id": image_id,
            "modality": "handwritten",
            "level": "word",
            "language": "odia",
            "model-id": "1",
            "meta": {"device": 0}
        }]
        infer_resp = requests.post(OCR_INFERENCE_URL, json=payload)

        if infer_resp.status_code != 200:
            return jsonify({'error': 'OCR inference failed', 'details': infer_resp.text}), 500

        ocr_text = infer_resp.json()['data'][0].get('text', '')
        print("OCR Output:", ocr_text)

        # Step 3: Translate using IndicTrans2
        trans_payload = {
            "input": [ocr_text],
            "src_lang": "ory_Orya",
            "tgt_lang": "eng_Latn"
        }
        trans_resp = requests.post(TRANSLATION_API_URL, json=trans_payload)

        if trans_resp.status_code != 200:
            print("Translation error response:")
            print("Status Code:", trans_resp.status_code)
            print("Headers:", trans_resp.headers)
            print("Body:", trans_resp.text)
            return jsonify({'error': 'Translation failed', 'details': trans_resp.text}), 500

        translated_text = trans_resp.json().get('output', [''])[0]
        print(translated_text)

        # Step 4: Return both OCR and translated text
        return jsonify({
            'ocr_text': ocr_text,
            'translated_text': translated_text
        })

    except Exception as e:
        print("Unexpected error:", str(e))
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)