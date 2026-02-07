from flask import Flask, request, jsonify, send_file
import os
import json
import zipfile
import base64
from io import BytesIO
import subprocess
from html.parser import HTMLParser
import re

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -----------------------------
# HTML parser
# -----------------------------
class HTMLExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.buttons = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'img' and 'src' in attrs_dict:
            self.images.append(attrs_dict['src'])
        elif tag == 'button' and 'id' in attrs_dict:
            self.buttons.append(attrs_dict['id'])

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())

# -----------------------------
# OGG → WAV conversion
# -----------------------------
def convert_ogg_to_wav(ogg_path):
    wav_path = ogg_path.replace('.ogg', '.wav')
    try:
        subprocess.run(['ffmpeg', '-y', '-i', ogg_path, wav_path], check=True)
        return wav_path
    except subprocess.CalledProcessError:
        print(f"Error converting {ogg_path} to WAV")
        return None

# -----------------------------
# Extract JS function names
# -----------------------------
def extract_js_functions(js_content):
    pattern = r'function\s+([a-zA-Z0-9_]+)\s*\('
    return re.findall(pattern, js_content)

# -----------------------------
# Create Scratch project
# -----------------------------
def create_sb3_project(html_files, js_files, assets):
    # Collect JS function names for placeholder blocks
    js_functions = []
    for js_file in js_files:
        try:
            content = open(js_file, 'r', encoding='utf-8', errors='ignore').read()
            js_functions += extract_js_functions(content)
        except:
            continue

    project = {
        "targets": [{
            "isStage": True,
            "name": "Stage",
            "variables": {},
            "lists": {},
            "broadcasts": {},
            "blocks": {},
            "comments": {},
            "currentCostume": 0,
            "costumes": [{
                "assetId": "cd21514d0531fdffb22204e0ec5529a3",
                "name": "backdrop1",
                "md5ext": "cd21514d0531fdffb22204e0ec5529a3.svg",
                "dataFormat": "svg",
                "rotationCenterX": 240,
                "rotationCenterY": 180
            }],
            "sounds": [],
            "volume": 100
        }],
        "monitors": [],
        "extensions": [],
        "meta": {
            "semver": "3.0.0",
            "vm": "0.2.0",
            "agent": "HTML→SB3 Converter"
        }
    }

    # Add assets
    for asset in assets:
        if asset.lower().endswith(('.wav', '.mp3')):
            try:
                with open(asset, 'rb') as f:
                    data_b64 = base64.b64encode(f.read()).decode()
                project["targets"][0]["sounds"].append({
                    "assetId": data_b64[:32],
                    "name": os.path.basename(asset),
                    "md5ext": f"{os.path.basename(asset)}.wav",
                    "dataFormat": "wav",
                    "rate": 48000,
                    "sampleCount": 100000
                })
            except:
                pass
        elif asset.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
            try:
                with open(asset, 'rb') as f:
                    data_b64 = base64.b64encode(f.read()).decode()
                project["targets"][0]["costumes"].append({
                    "assetId": data_b64[:32],
                    "name": os.path.basename(asset),
                    "md5ext": os.path.basename(asset),
                    "dataFormat": asset.split('.')[-1],
                    "rotationCenterX": 0,
                    "rotationCenterY": 0
                })
            except:
                pass

    # Add placeholder blocks for JS functions
    for func in js_functions:
        block_id = func + "_placeholder"
        project["targets"][0]["blocks"][block_id] = {
            "opcode": "procedures_define",
            "next": None,
            "parent": None,
            "inputs": {},
            "fields": {"NAME": [func, func]},
            "shadow": False,
            "topLevel": True,
            "x": 10,
            "y": 10
        }

    return project

# -----------------------------
# Routes
# -----------------------------
@app.route('/')
def home():
    return open('index.html', 'r').read()

@app.route('/convert', methods=['POST'])
def convert():
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files uploaded'}), 400

        html_files, js_files, assets = [], [], []

        for file in files:
            filename = file.filename
            ext = filename.lower().split('.')[-1]
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)

            if ext == 'html':
                html_files.append(save_path)
            elif ext == 'js':
                js_files.append(save_path)
            elif ext in ['ogg']:
                wav = convert_ogg_to_wav(save_path)
                if wav:
                    assets.append(wav)
            elif ext in ['wav', 'mp3', 'png', 'jpg', 'jpeg', 'gif', 'svg']:
                assets.append(save_path)

        # Create SB3
        project = create_sb3_project(html_files, js_files, assets)

        # Write SB3 zip
        sb3_bytes = BytesIO()
        with zipfile.ZipFile(sb3_bytes, 'w') as zf:
            zf.writestr('project.json', json.dumps(project))
            for asset in assets:
                try:
                    zf.write(asset, arcname=os.path.basename(asset))
                except:
                    continue
        sb3_bytes.seek(0)

        return send_file(
            sb3_bytes,
            mimetype='application/zip',
            as_attachment=True,
            download_name='project.sb3'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -----------------------------
# Run app
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
