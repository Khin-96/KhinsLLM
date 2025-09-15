# vision_tools.py
import cv2
import numpy as np
from typing import Optional, List, Dict, Any
import logging
from livekit.agents import function_tool, RunContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisionProcessor:
    def __init__(self):
        self.initialized = True
        logger.info("Vision processor initialized with OpenCV only")
    
    def count_fingers(self, frame: np.ndarray) -> Optional[int]:
        """Count fingers using contour analysis (OpenCV only)"""
        try:
            # Convert to grayscale and apply threshold
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Use adaptive thresholding for better results
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY_INV, 11, 2)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Find the largest contour (likely a hand)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Filter by area to avoid small noise
            if cv2.contourArea(largest_contour) < 1000:
                return None
            
            # Find convex hull and defects
            hull = cv2.convexHull(largest_contour, returnPoints=False)
            if hull is None or len(hull) < 3:
                return None
            
            try:
                defects = cv2.convexityDefects(largest_contour, hull)
                if defects is None:
                    return None
                
                # Count defects (each defect typically represents a finger)
                finger_count = 0
                for i in range(defects.shape[0]):
                    s, e, f, d = defects[i, 0]
                    if d > 1000:  # Filter by defect depth
                        finger_count += 1
                
                # Add 1 for the thumb (basic approximation)
                return min(finger_count + 1, 5)
                
            except:
                # Fallback: estimate fingers based on contour area
                area = cv2.contourArea(largest_contour)
                if area < 5000:
                    return 1
                elif area < 10000:
                    return 2
                elif area < 15000:
                    return 3
                elif area < 20000:
                    return 4
                else:
                    return 5
                    
        except Exception as e:
            logger.error(f"Error counting fingers: {e}")
            return None
    
    def detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect objects by color using OpenCV"""
        objects = []
        
        try:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Define color ranges (HSV format)
            color_ranges = {
                "red": ([0, 120, 70], [10, 255, 255]),
                "blue": ([100, 120, 70], [130, 255, 255]),
                "green": ([40, 40, 40], [80, 255, 255]),
                "yellow": ([20, 100, 100], [30, 255, 255]),
                "white": ([0, 0, 200], [180, 30, 255]),
                "black": ([0, 0, 0], [180, 255, 50])
            }
            
            for color_name, (lower, upper) in color_ranges.items():
                lower_np = np.array(lower)
                upper_np = np.array(upper)
                mask = cv2.inRange(hsv, lower_np, upper_np)
                
                # Remove noise
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > 1000:  # Minimum area threshold
                        x, y, w, h = cv2.boundingRect(contour)
                        objects.append({
                            "type": f"{color_name}_object",
                            "area": area,
                            "color": color_name,
                            "position": (x, y, w, h)
                        })
            
            return objects
            
        except Exception as e:
            logger.error(f"Error detecting objects: {e}")
            return []
    
    def describe_scene(self, frame: np.ndarray) -> str:
        """Generate a basic description of the scene"""
        try:
            # Analyze image properties
            brightness = np.mean(frame)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            saturation = np.mean(hsv[:, :, 1])
            
            # Edge detection for detail analysis
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Color analysis
            dominant_color = self._get_dominant_color(frame)
            
            description = "I see "
            if brightness > 180:
                description += "a bright scene"
            elif brightness < 80:
                description += "a dark scene"
            else:
                description += "a moderately lit scene"
                
            if saturation > 120:
                description += " with vivid colors"
            elif saturation < 50:
                description += " with muted colors"
            else:
                description += " with normal colors"
                
            if edge_density > 0.15:
                description += " containing many details"
            elif edge_density < 0.05:
                description += " with smooth surfaces"
                
            description += f". The dominant color is {dominant_color}."
            
            return description
            
        except Exception as e:
            logger.error(f"Error describing scene: {e}")
            return "I'm having trouble analyzing the scene."
    
    def _get_dominant_color(self, frame: np.ndarray) -> str:
        """Get the dominant color in the frame"""
        try:
            # Resize for faster processing
            small = cv2.resize(frame, (100, 100))
            
            # Convert to HSV and get the most common hue
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            hues = hsv[:, :, 0].flatten()
            
            # Map hue values to color names
            hue_bins = {
                (0, 15): "red",
                (16, 35): "orange",
                (36, 70): "yellow",
                (71, 85): "green",
                (86, 135): "blue",
                (136, 165): "purple",
                (166, 180): "pink"
            }
            
            # Find most common hue range
            hist, _ = np.histogram(hues, bins=180)
            dominant_hue = np.argmax(hist)
            
            for (low, high), color in hue_bins.items():
                if low <= dominant_hue <= high:
                    return color
            
            return "unknown"
            
        except:
            return "unknown"
    
    def detect_faces(self, frame: np.ndarray) -> Dict[str, Any]:
        """Detect faces using Haar cascades"""
        faces = []
        
        try:
            # Load pre-trained face detector
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            detected_faces = face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            for (x, y, w, h) in detected_faces:
                faces.append({
                    "bounding_box": {
                        "x": x / frame.shape[1],
                        "y": y / frame.shape[0],
                        "width": w / frame.shape[1],
                        "height": h / frame.shape[0]
                    },
                    "confidence": 0.8  # Estimated confidence
                })
            
            return {
                "face_count": len(faces),
                "faces": faces,
                "emotions": ["neutral"] * len(faces)  # Basic placeholder
            }
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return {"face_count": 0, "faces": [], "emotions": []}
    
    def read_text(self, frame: np.ndarray) -> str:
        """Simple text detection using contour analysis"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # Find contours that might be text
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            text_contours = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                area = cv2.contourArea(contour)
                
                # Text-like characteristics
                if (0.1 < aspect_ratio < 10.0 and  # Reasonable aspect ratio
                    20 < area < 5000 and           # Reasonable size
                    h > 10 and w > 5):             # Minimum dimensions
                    text_contours.append(contour)
            
            if len(text_contours) > 3:
                return "I see some text-like patterns, but cannot read them clearly."
            else:
                return "No readable text found."
                
        except Exception as e:
            return f"Error analyzing text: {str(e)}"

# Global vision processor instance
vision_processor = VisionProcessor()

def capture_frame():
    """Capture a frame from the default camera with error handling"""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            # Try different camera indices
            for i in range(1, 4):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    break
            
            if not cap.isOpened():
                return None, "I can't access any camera. Please make sure a camera is connected."
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Allow camera to warm up
        for _ in range(5):
            cap.read()
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            return None, "I couldn't capture an image from the camera."
        
        return frame, None
        
    except Exception as e:
        return None, f"Camera error: {str(e)}"

@function_tool()
async def count_fingers(context: RunContext) -> str:
    """Count fingers in the camera view"""
    frame, error = capture_frame()
    if error:
        return error
    
    finger_count = vision_processor.count_fingers(frame)
    
    if finger_count is None:
        return "I don't see any hands. Please show your hand clearly to the camera."
    
    return f"You're holding up {finger_count} finger{'s' if finger_count != 1 else ''}."

@function_tool()
async def detect_objects(context: RunContext) -> str:
    """Detect colored objects"""
    frame, error = capture_frame()
    if error:
        return error
    
    objects = vision_processor.detect_objects(frame)
    
    if not objects:
        return "I don't see any distinct objects. Try showing me colorful items."
    
    # Group by color
    color_groups = {}
    for obj in objects:
        color = obj["color"]
        if color not in color_groups:
            color_groups[color] = 0
        color_groups[color] += 1
    
    response = "I see "
    items = []
    for color, count in color_groups.items():
        items.append(f"{count} {color} object{'s' if count > 1 else ''}")
    
    response += ", ".join(items)
    return response

@function_tool()
async def describe_scene(context: RunContext) -> str:
    """Describe the current scene"""
    frame, error = capture_frame()
    if error:
        return error
    
    return vision_processor.describe_scene(frame)

@function_tool()
async def detect_faces(context: RunContext) -> str:
    """Detect faces"""
    frame, error = capture_frame()
    if error:
        return error
    
    faces_info = vision_processor.detect_faces(frame)
    
    if faces_info["face_count"] == 0:
        return "I don't see any faces. Please make sure faces are visible to the camera."
    
    response = f"I see {faces_info['face_count']} face{'s' if faces_info['face_count'] != 1 else ''}."
    return response

@function_tool()
async def read_text(context: RunContext) -> str:
    """Simple text detection"""
    frame, error = capture_frame()
    if error:
        return error
    
    return vision_processor.read_text(frame)

# Test the module
if __name__ == "__main__":
    print("Vision Tools Module")
    print("Testing camera access...")
    
    frame, error = capture_frame()
    if error:
        print(f"Error: {error}")
    else:
        print("Camera access successful!")
        print(f"Frame shape: {frame.shape}")
        
    print("\nAvailable functions:")
    print("count_fingers() - Count fingers in camera view")
    print("detect_objects() - Detect colored objects")
    print("describe_scene() - Describe the scene")
    print("detect_faces() - Detect faces")
    print("read_text() - Basic text detection")