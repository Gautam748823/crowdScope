from flask import Flask, Response, render_template, jsonify, request
import cv2
import numpy as np
import os
from flask_cors import CORS
import time

# Import our detector module
from detector import MotionDetector

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)  # Enable CORS for all routes

# Create detector instance with default configuration
detector = MotionDetector()

def generate_frames():
    """Generate frames for video streaming"""
    while True:
        # Get the current frame from the detector
        frame = detector.get_frame()
        
        # If no frame is available, wait briefly and try again
        if frame is None:
            time.sleep(0.03)
            continue
            
        # Encode the frame as JPEG
        (flag, encoded_image) = cv2.imencode(".jpg", frame)
        if not flag:
            continue
            
        # Yield the frame in HTTP multipart response format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encoded_image) + b'\r\n')
        
        # Short delay to control frame rate
        time.sleep(0.03)  # ~30fps

@app.route('/')
def index():
    """Serve the main page"""
    return app.send_static_file('index.html')

@app.route('/video_feed')
def video_feed():
    """Stream the video feed"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def get_status():
    """Get the current system status"""
    return jsonify(detector.get_status())

@app.route('/recordings')
def get_recordings():
    """Get the list of recordings"""
    return jsonify(detector.get_recordings())
    
@app.route('/config', methods=['POST'])
def update_config():
    """Update detector configuration"""
    try:
        new_config = request.json
        detector.update_config(new_config)
        return jsonify({"success": True, "message": "Configuration updated"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/start', methods=['POST'])
def start_detection():
    """Start the motion detection"""
    try:
        detector.start()
        return jsonify({"success": True, "message": "Detection started"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop_detection():
    """Stop the motion detection"""
    try:
        detector.stop()
        return jsonify({"success": True, "message": "Detection stopped"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    # Start motion detection
    detector.start()
    
    # Run Flask app
    try:
        app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=False)
    finally:
        # Ensure we stop the detector when the app exits
        detector.stop()