# converter.py

"""
Website Directory → Scratch .sb3 Converter
Converts HTML/JS/CSS website folders into a Scratch 3 project skeleton.
Includes OGG → WAV conversion and automatic asset injection.
"""

import os
import zipfile
import json
import base64
import subprocess
import re
from io import BytesIO
from html.parser import HTMLParser

# -----------------------------
# HTML Parser
# -----------------------------
class HTMLExtractor(HTMLParser):
    """
    Extracts images, buttons, and text from HTML files.
    """
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
# Audio conversion
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
# JS parser for placeholder blocks
# -----------------------------
def extract_js_functions(js_content):
    """
    Extracts all top-level JS function names to create placeholder blocks in Scratch.
    """
    pattern = r'function\s+([a-zA-Z0-9_]+)\s*\('
    return re.findall(pattern, js_content)

# -----------------------------
# SB3 Project Creation
# -----------------------------
def create_sb3_project(html_files, js_files, assets):
    """
    Generates a minimal Scratch 3.0 project JSON skeleton.
    """
    # Extract JS function names
    js_functions = []
    for js_file in js_files:
        try:
            content = open(js_file, 'r', encoding='utf-8', errors='ignore').read()
            js_functions += extract_js_functions(content)
        except:
            continue

    # Base project
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
            "agent": "Website→SB3 Converter"
        }
    }

    # Add audio assets
    for asset in assets:
        if asset.endswith(('.wav', '.mp3')):
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

    # Add image assets as costumes
    for asset in assets:
        if asset.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
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

    # Create placeholder blocks for JS functions
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
# Main converter function
# -----------------------------
def convert_directory_to_sb3(directory_path, output_path="project.sb3"):
    """
    Convert a website directory to a Scratch .sb3 file.
    """
    html_files = []
    js_files = []
    assets = []

    # Walk the directory
    for root, _, files in os.walk(directory_path):
        for file in files:
            filepath = os.path.join(root, file)
            if file.lower().endswith('.html'):
                html_files.append(filepath)
            elif file.lower().endswith('.js'):
                js_files.append(filepath)
            elif file.lower().endswith('.ogg'):
                wav = convert_ogg_to_wav(filepath)
                if wav:
                    assets.append(wav)
            elif file.lower().endswith(('.wav', '.mp3', '.png', '.jpg', '.jpeg', '.gif', '.svg')):
                assets.append(filepath)

    # Parse HTML files for completeness (optional)
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                parser = HTMLExtractor()
                parser.feed(content)
        except:
            continue

    # Generate SB3 project JSON
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

    # Save to disk
    with open(output_path, 'wb') as f:
        f.write(sb3_bytes.getbuffer())

    print(f"✅ Conversion complete! Saved to {output_path}")

# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    directory = input("Enter website directory path: ")
    convert_directory_to_sb3(directory)
