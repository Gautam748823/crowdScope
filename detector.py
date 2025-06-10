import cv2
import numpy as np
import datetime
import os
import time
import threading

class MotionDetector:
    def __init__(self, config=None):
        # Default configuration
        self.config = {
            'motion_threshold': 25,
            'min_contour_area': 2000,
            'record_seconds_after_motion': 2,
            'output_folder': 'motion_recordings',
            'fps': 20,
            'frame_width': 640,
            'frame_height': 480
        }
        
        # Override with user config if provided
        if config:
            self.config.update(config)
            
        # Ensure output directory exists
        if not os.path.exists(self.config['output_folder']):
            os.makedirs(self.config['output_folder'])
            
        # Load face cascade classifier
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize variables
        self.camera = None
        self.output_frame = None
        self.lock = threading.Lock()
        self.recording = False
        self.out = None
        self.motion_detected_time = None
        self.last_frame = None
        self.head_count = 0
        self.status = "Monitoring"
        self.motion_status = "No Motion"
        self.running = False
        self.detection_thread = None
        
    def init_camera(self):
        """Initialize the webcam capture"""
        self.camera = cv2.VideoCapture(0)  # Use 0 for default webcam
        if not self.camera.isOpened():
            raise RuntimeError("Could not open webcam. Please check your camera connection.")
        return self.camera
        
    def release_camera(self):
        """Release the camera resource"""
        if self.camera and self.camera.isOpened():
            self.camera.release()
            self.camera = None
    
    def start(self):
        """Start the motion detection thread"""
        if self.running:
            return
            
        self.running = True
        self.detection_thread = threading.Thread(target=self._detection_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        return self.detection_thread
        
    def stop(self):
        """Stop the motion detection thread"""
        self.running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=1.0)
            self.detection_thread = None
            
        # Clean up recording if active
        if self.recording and self.out:
            self.out.release()
            self.recording = False
            
        # Release camera
        self.release_camera()
            
    def get_status(self):
        """Get the current status of the detector"""
        with self.lock:
            return {
                'recording': self.recording,
                'headCount': self.head_count,
                'status': self.status,
                'motionStatus': self.motion_status
            }
            
    def get_frame(self):
        """Get the current processed frame"""
        with self.lock:
            if self.output_frame is None:
                # Return a blank frame if no frame is available
                blank = np.zeros((
                    self.config['frame_height'], 
                    self.config['frame_width'], 
                    3
                ), dtype=np.uint8)
                return blank
            return self.output_frame.copy()
    
    def get_recordings(self):
        """Get a list of recorded video files"""
        if not os.path.exists(self.config['output_folder']):
            return []
        
        files = os.listdir(self.config['output_folder'])
        recordings = [f for f in files if f.endswith('.avi')]
        recordings.sort(reverse=True)  # Most recent first
        
        return recordings
    
    def update_config(self, new_config):
        """Update detector configuration"""
        self.config.update(new_config)
    
    def _detection_loop(self):
        """Main detection loop that runs in a separate thread"""
        # Initialize camera if not already initialized
        if self.camera is None:
            self.camera = self.init_camera()
        
        while self.running:
            # Read frame from camera
            success, frame = self.camera.read()
            if not success:
                print("Failed to capture frame from camera")
                time.sleep(0.1)  # Short delay before trying again
                continue
                
            # Resize frame for consistency
            frame = cv2.resize(frame, (
                self.config['frame_width'], 
                self.config['frame_height']
            ))
            
            # Process the frame
            self._process_frame(frame)
            
            # Control frame rate
            time.sleep(1 / self.config['fps'])
    
    def _process_frame(self, frame):
        """Process a single frame for motion detection and face recognition"""
        # Convert to grayscale for motion detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Initialize last_frame if needed
        if self.last_frame is None:
            self.last_frame = gray
            return
            
        # Compute frame difference for motion detection
        frame_diff = cv2.absdiff(self.last_frame, gray)
        _, threshold = cv2.threshold(frame_diff, self.config['motion_threshold'], 255, cv2.THRESH_BINARY)
        threshold = cv2.dilate(threshold, None, iterations=2)
        
        # Find contours for motion detection
        contours, _ = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find largest contour
        largest_contour = None
        max_area = 0
        motion_detected = False
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area and area > self.config['min_contour_area']:
                max_area = area
                largest_contour = contour
                motion_detected = True
                
        # Draw largest contour if detected
        if largest_contour is not None:
            (x, y, w, h) = cv2.boundingRect(largest_contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
        # Update last frame
        self.last_frame = gray
        
        current_time = datetime.datetime.now()
        
        # Handle motion detection and recording
        if motion_detected:
            self.motion_status = "MOTION DETECTED!"
            self.motion_detected_time = current_time
            if not self.recording:
                self.recording = True
                filename = f"{self.config['output_folder']}/motion_{current_time.strftime('%Y%m%d_%H%M%S')}.avi"
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                self.out = cv2.VideoWriter(
                    filename, 
                    fourcc, 
                    self.config['fps'], 
                    (self.config['frame_width'], self.config['frame_height'])
                )
                print(f"Recording: {filename}")
                self.status = "RECORDING"
        else:
            self.motion_status = "No Motion"
                
        if self.recording:
            self.out.write(frame)
            if self.motion_detected_time and (current_time - self.motion_detected_time).seconds >= self.config['record_seconds_after_motion']:
                self.recording = False
                self.out.release()
                print("Recording saved.")
                self.status = "Monitoring"
                
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        self.head_count = len(faces)
        
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            
        # Add text information to frame
        cv2.putText(frame, f"Status: {self.status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Heads detected: {self.head_count}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, current_time.strftime("%Y-%m-%d %H:%M:%S"), (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        if motion_detected:
            cv2.putText(frame, "MOTION DETECTED!", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
        # Update the output frame
        with self.lock:
            self.output_frame = frame.copy()