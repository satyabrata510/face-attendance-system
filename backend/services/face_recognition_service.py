"""
Face Recognition Service

This service handles face detection and recognition.
Uses face_recognition library if available, otherwise provides mock functionality.
"""

import numpy as np
from PIL import Image
import io
from typing import List, Tuple, Optional
import pickle

# Try to import face_recognition, fall back to mock if not available
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: face_recognition library not available. Using mock mode.")
    print("To enable real face recognition, install: pip install face_recognition")
    print("Note: This requires cmake and dlib. On macOS: brew install cmake")


class FaceRecognitionService:
    """Service for face detection and recognition operations."""
    
    def __init__(self, tolerance: float = 0.6):
        """
        Initialize the face recognition service.
        
        Args:
            tolerance: How much distance between faces to consider a match.
                      Lower is more strict. Default 0.6.
        """
        self.tolerance = tolerance
        self.mock_mode = not FACE_RECOGNITION_AVAILABLE
    
    def encode_face(self, image_bytes: bytes) -> Optional[bytes]:
        """
        Extract face encoding from an image.
        
        Args:
            image_bytes: The image data as bytes.
            
        Returns:
            Serialized face encoding as bytes, or None if no face found.
        """
        if self.mock_mode:
            # In mock mode, generate a random encoding for testing
            encoding = np.random.rand(128).astype(np.float64)
            return pickle.dumps(encoding)
        
        try:
            # Load image from bytes
            image = face_recognition.load_image_file(io.BytesIO(image_bytes))
            
            # Find face locations and encodings
            face_locations = face_recognition.face_locations(image)
            
            if len(face_locations) == 0:
                return None
            
            if len(face_locations) > 1:
                # If multiple faces, take the largest one
                areas = [(loc[2] - loc[0]) * (loc[1] - loc[3]) for loc in face_locations]
                largest_idx = areas.index(max(areas))
                face_locations = [face_locations[largest_idx]]
            
            # Get encoding for the face
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if len(face_encodings) == 0:
                return None
            
            # Serialize the encoding
            return pickle.dumps(face_encodings[0])
            
        except Exception as e:
            print(f"Error encoding face: {e}")
            return None
    
    def compare_faces(
        self, 
        known_encodings: List[Tuple[int, bytes]], 
        unknown_image_bytes: bytes,
        sensitivity: int = 75
    ) -> List[Tuple[int, float]]:
        """
        Compare an unknown face against known face encodings.
        
        Args:
            known_encodings: List of (student_id, serialized_encoding) tuples.
            unknown_image_bytes: The image data as bytes to match.
            sensitivity: Recognition sensitivity (50-100). Higher = stricter matching.
            
        Returns:
            List of (student_id, confidence) for matched faces.
        """
        if self.mock_mode:
            # In mock mode, return matches for all known faces with random confidence
            matches = []
            for student_id, _ in known_encodings:
                confidence = float(round(np.random.uniform(80, 99), 1))
                matches.append((student_id, confidence))
            return matches[:1] if matches else []  # Return at most 1 match in mock mode
        
        try:
            # Adjust tolerance based on sensitivity
            # Sensitivity 50 = tolerance 0.8 (loose)
            # Sensitivity 100 = tolerance 0.4 (strict)
            tolerance = 0.8 - (sensitivity - 50) * 0.008
            
            # Load and encode the unknown image
            image = face_recognition.load_image_file(io.BytesIO(unknown_image_bytes))
            face_locations = face_recognition.face_locations(image)
            
            if len(face_locations) == 0:
                return []
            
            unknown_encodings = face_recognition.face_encodings(image, face_locations)
            
            matches = []
            
            # Deserialize known encodings
            known_faces = []
            student_ids = []
            for student_id, encoding_bytes in known_encodings:
                try:
                    encoding = pickle.loads(encoding_bytes)
                    known_faces.append(encoding)
                    student_ids.append(student_id)
                except:
                    continue
            
            if not known_faces:
                return []
            
            # Compare each detected face with known faces
            for unknown_encoding in unknown_encodings:
                # Calculate face distances
                face_distances = face_recognition.face_distance(known_faces, unknown_encoding)
                
                # Find the best match
                best_match_idx = np.argmin(face_distances)
                best_distance = face_distances[best_match_idx]
                
                if best_distance <= tolerance:
                    # Convert distance to confidence percentage - ensure it's a standard float
                    confidence = float(round((1 - best_distance) * 100, 1))
                    matches.append((student_ids[best_match_idx], confidence))
                else:
                    print(f"DEBUG: Face distance {best_distance} > {tolerance}. Strict match failed.")

            return matches
            
        except Exception as e:
            print(f"Error comparing faces: {e}")
            return []
    
    def detect_faces(self, image_bytes: bytes) -> int:
        """
        Detect the number of faces in an image.
        
        Args:
            image_bytes: The image data as bytes.
            
        Returns:
            Number of faces detected.
        """
        if self.mock_mode:
            # In mock mode, assume 1 face is always detected
            return 1
        
        try:
            image = face_recognition.load_image_file(io.BytesIO(image_bytes))
            face_locations = face_recognition.face_locations(image)
            return len(face_locations)
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return 0
    
    def validate_face_image(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate that an image is suitable for face registration.
        
        Args:
            image_bytes: The image data as bytes.
            
        Returns:
            Tuple of (is_valid, message).
        """
        if self.mock_mode:
            # In mock mode, accept all images
            try:
                image = Image.open(io.BytesIO(image_bytes))
                width, height = image.size
                if width < 100 or height < 100:
                    return False, "Image is too small. Minimum size is 100x100 pixels."
                return True, "Image is valid for face registration (mock mode)."
            except Exception as e:
                return False, f"Error processing image: {str(e)}"
        
        try:
            # Check image can be loaded
            image = face_recognition.load_image_file(io.BytesIO(image_bytes))
            
            # Check image size
            height, width = image.shape[:2]
            if width < 100 or height < 100:
                return False, "Image is too small. Minimum size is 100x100 pixels."
            
            # Detect faces
            face_locations = face_recognition.face_locations(image)
            
            if len(face_locations) == 0:
                return False, "No face detected in the image."
            
            if len(face_locations) > 1:
                return False, f"Multiple faces ({len(face_locations)}) detected. Please provide an image with only one face."
            
            # Check face size relative to image
            top, right, bottom, left = face_locations[0]
            face_width = right - left
            face_height = bottom - top
            
            if face_width < 50 or face_height < 50:
                return False, "Face is too small in the image. Please provide a clearer close-up photo."
            
            return True, "Image is valid for face registration."
            
        except Exception as e:
            return False, f"Error processing image: {str(e)}"
    
    def is_mock_mode(self) -> bool:
        """Check if service is running in mock mode."""
        return self.mock_mode


# Global instance
face_service = FaceRecognitionService()
