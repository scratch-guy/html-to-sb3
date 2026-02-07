from flask import Flask, request, jsonify
import os
from pydub import AudioSegment

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to HTML to SB3 Converter"

@app.route('/convert', methods=['POST'])
def convert():
    html_file = request.files['file']
    ogg_audio = request.files['audio']

    # Save HTML file
    html_path = os.path.join('uploads', html_file.filename)
    html_file.save(html_path)

    # Convert OGG to WAV
    ogg_path = os.path.join('uploads', ogg_audio.filename)
    ogg_audio.save(ogg_path)
    wav_path = ogg_path.replace('.ogg', '.wav')
    audio = AudioSegment.from_ogg(ogg_path)
    audio.export(wav_path, format='wav')

    # Here you can add the logic to handle HTML and do the conversion to SB3 here

    return jsonify({'message': 'Conversion complete', 'wav_file': wav_path})

if __name__ == '__main__':
    app.run(debug=True)