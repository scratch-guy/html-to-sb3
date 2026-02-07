from flask import Flask, request, jsonify, send_file
import os
import json
import zipfile
import base64
from io import BytesIO
from pydub import AudioSegment
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

class HTMLExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.images = []
        self.buttons = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            attrs_dict = dict(attrs)
            self.images.append(attrs_dict.get('src', ''))
        elif tag == 'button':
            attrs_dict = dict(attrs)
            self.buttons.append(attrs_dict.get('id', ''))
    
    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())

def convert_ogg_to_wav(ogg_path):
    try:
        audio = AudioSegment.from_ogg(ogg_path)
        wav_path = ogg_path.replace('.ogg', '.wav')
        audio.export(wav_path, format='wav')
        return wav_path
    except Exception as e:
        print(f"Error converting OGG to WAV: {e}")
        return None

def create_sb3_project(html_content, assets):
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
            "agent": "Mozilla/5.0"
        }
    }
    
    # Add audio assets
    for asset in assets:
        if asset.endswith('.wav'):
            project["targets"][0]["sounds"].append({
                "assetId": base64.b64encode(open(asset, 'rb').read()).decode(),
                "name": os.path.basename(asset),
                "md5ext": f"{os.path.basename(asset)}.wav",
                "dataFormat": "wav",
                "rate": 48000,
                "sampleCount": 100000
            })
    
    return project

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>HTML to SB3 Converter</title>
        <style>
            body { font-family: Arial; margin: 40px; }
            form { border: 1px solid #ccc; padding: 20px; }
            input { padding: 10px; margin: 10px 0; }
            button { padding: 10px 20px; background: #4CAF50; color: white; }
        </style>
    </head>
    <body>
        <h1>HTML to SB3 Converter</h1>
        <form id="uploadForm">
            <label>Upload Directory:</label>
            <input type="file" id="fileUpload" webkitdirectory directory multiple required>
            <button type="submit">Convert to SB3</button>
        </form>
        <div id="status"></div>
        <script>
            document.getElementById('uploadForm').onsubmit = async function(e) {
                e.preventDefault();
                const files = document.getElementById('fileUpload').files;
                const formData = new FormData();
                
                for (let i = 0; i < files.length; i++) {
                    formData.append('files', files[i]);
                }
                
                document.getElementById('status').innerHTML = 'Converting...';
                
                try {
                    const response = await fetch('/convert', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'project.sb3';
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.getElementById('status').innerHTML = 'Conversion complete! Download started.';
                    } else {
                        document.getElementById('status').innerHTML = 'Error: ' + response.statusText;
                    }
                } catch (error) {
                    document.getElementById('status').innerHTML = 'Error: ' + error.message;
                }
            };
        </script>
    </body>
    </html>
    '''

@app.route('/convert', methods=['POST'])
def convert():
    try:
        files = request.files.getlist('files')
        
        html_files = []
        css_files = []
        js_files = []
        audio_files = []
        image_files = []
        assets = []
        
        # Organize files by type
        for file in files:
            if file.filename.endswith('.html'):
                html_files.append(file)
            elif file.filename.endswith('.css'):
                css_files.append(file)
            elif file.filename.endswith('.js'):
                js_files.append(file)
            elif file.filename.endswith('.ogg'):
                # Convert OGG to WAV
                ogg_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(ogg_path)
                wav_path = convert_ogg_to_wav(ogg_path)
                if wav_path:
                    audio_files.append(wav_path)
                    assets.append(wav_path)
            elif file.filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(img_path)
                image_files.append(img_path)
                assets.append(img_path)
        
        # Parse HTML
        html_content = ""
        if html_files:
            for html_file in html_files:
                html_content += html_file.read().decode('utf-8')
        
        # Create SB3 project
        project = create_sb3_project(html_content, assets)
        
        # Create SB3 file (zip format)
        sb3_output = BytesIO()
        with zipfile.ZipFile(sb3_output, 'w') as zf:
            # Write project.json
            zf.writestr('project.json', json.dumps(project))
            
            # Add assets
            for asset in assets:
                if os.path.exists(asset):
                    zf.write(asset, arcname=os.path.basename(asset))
        
        sb3_output.seek(0)
        
        return send_file(
            sb3_output,
            mimetype='application/zip',
            as_attachment=True,
            download_name='project.sb3'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True}
