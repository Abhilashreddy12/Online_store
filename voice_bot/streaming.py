"""
Real-time audio streaming utilities

Features:
- Audio buffering
- Chunk processing
- Real-time transcription windows
- Progressive confidence tracking
"""

import logging
import io
from collections import deque
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class StreamingAudioBuffer:
    """
    Buffers audio chunks for real-time processing
    
    Features:
    - Configurable buffer size
    - Sliding window transcription
    - Overlap handling
    """
    
    def __init__(self, sample_rate: int = 16000, chunk_duration_ms: int = 100):
        """
        Initialize audio buffer
        
        Args:
            sample_rate: Audio sample rate (Hz)
            chunk_duration_ms: Duration of each chunk in milliseconds
        """
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_size = int(sample_rate * chunk_duration_ms / 1000)
        
        self.buffer = deque(maxlen=100)  # Keep last 100 chunks (~10 seconds at 100ms)
        self.total_bytes = 0
    
    def add_chunk(self, audio_chunk: bytes) -> int:
        """
        Add audio chunk to buffer
        
        Args:
            audio_chunk: Binary audio data
        
        Returns:
            Total bytes in buffer
        """
        self.buffer.append(audio_chunk)
        self.total_bytes += len(audio_chunk)
        return self.total_bytes
    
    def get_accumulated_audio(self) -> bytes:
        """Get all accumulated audio as single bytes object"""
        return b''.join(self.buffer)
    
    def get_buffered_duration_seconds(self) -> float:
        """Estimate buffered audio duration"""
        total_samples = self.total_bytes // 2  # Assuming 16-bit audio
        return total_samples / self.sample_rate
    
    def clear(self):
        """Clear buffer"""
        self.buffer.clear()
        self.total_bytes = 0


class PartialTranscriptionManager:
    """
    Manages partial (incremental) transcription updates
    
    Features:
    - Track confidence changes
    - Detect stable segments
    - Update only changed parts
    """
    
    def __init__(self):
        """Initialize manager"""
        self.full_text = ""
        self.last_confidence = 0.0
        self.confidence_history = []
    
    def update(self, new_text: str, confidence: float) -> dict:
        """
        Update transcription
        
        Returns:
            {
                'full_text': complete transcription,
                'new_segment': newly transcribed text,
                'confidence': confidence score,
                'is_stable': bool (confidence not changing much),
                'confidence_trend': 'improving' | 'stable' | 'declining'
            }
        """
        self.confidence_history.append(confidence)
        
        # Keep last 5 readings
        if len(self.confidence_history) > 5:
            self.confidence_history.pop(0)
        
        # Calculate trend
        if len(self.confidence_history) >= 2:
            recent = self.confidence_history[-1]
            previous = self.confidence_history[-2]
            
            if recent > previous + 0.05:
                trend = 'improving'
            elif recent < previous - 0.05:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        # Determine if stable
        is_stable = trend == 'stable' or len(self.confidence_history) >= 3
        
        # Find new segment
        if new_text.startswith(self.full_text):
            new_segment = new_text[len(self.full_text):]
        else:
            new_segment = new_text
        
        self.full_text = new_text
        self.last_confidence = confidence
        
        return {
            'full_text': self.full_text,
            'new_segment': new_segment,
            'confidence': confidence,
            'is_stable': is_stable,
            'confidence_trend': trend,
            'history_length': len(self.confidence_history)
        }
    
    def get_confidence_stability(self) -> float:
        """
        Get confidence stability score (0-1)
        
        Higher = more stable
        """
        if len(self.confidence_history) < 2:
            return 0.0
        
        # Calculate variance
        mean = sum(self.confidence_history) / len(self.confidence_history)
        variance = sum((x - mean) ** 2 for x in self.confidence_history) / len(self.confidence_history)
        
        # Convert variance to stability (inverse)
        stability = 1.0 / (1.0 + variance)
        return stability


class StreamingIntentDetector:
    """
    Detects intents from streaming transcription
    
    Features:
    - Progressive intent detection
    - Intent confidence tracking
    - Intent stability monitoring
    """
    
    def __init__(self):
        """Initialize detector"""
        self.detected_intents = []
        self.current_intent = None
        self.intent_confidence_history = {}
    
    def detect_intent(self, text: str, classifier) -> dict:
        """
        Detect intent from text
        
        Returns:
            {
                'intent': detected intent,
                'confidence': confidence score,
                'is_stable': bool,
                'changed': bool (intent changed),
                'candidates': top intents
            }
        """
        if not text:
            return {
                'intent': 'UNKNOWN',
                'confidence': 0.0,
                'is_stable': False,
                'changed': False,
                'candidates': []
            }
        
        # Classify
        intent, confidence, candidates = classifier.classify(text)
        
        # Track confidence
        if intent not in self.intent_confidence_history:
            self.intent_confidence_history[intent] = []
        
        self.intent_confidence_history[intent].append(confidence)
        conf_history = self.intent_confidence_history[intent]
        
        # Keep last 5
        if len(conf_history) > 5:
            conf_history.pop(0)
        
        # Determine stability
        is_stable = len(conf_history) >= 3
        
        # Check if intent changed
        changed = intent != self.current_intent
        self.current_intent = intent
        
        return {
            'intent': intent,
            'confidence': float(confidence),
            'is_stable': is_stable,
            'changed': changed,
            'candidates': candidates,
            'samples': len(conf_history)
        }


class StreamingProgressTracker:
    """
    Tracks streaming progress for client updates
    """
    
    def __init__(self):
        """Initialize tracker"""
        self.chunks_received = 0
        self.transcription_updates = 0
        self.intent_updates = 0
        self.start_time = None
    
    def add_chunk(self) -> int:
        """Record chunk received"""
        self.chunks_received += 1
        return self.chunks_received
    
    def add_transcription_update(self) -> int:
        """Record transcription update"""
        self.transcription_updates += 1
        return self.transcription_updates
    
    def add_intent_update(self) -> int:
        """Record intent update"""
        self.intent_updates += 1
        return self.intent_updates
    
    def get_progress(self) -> dict:
        """Get current progress"""
        return {
            'chunks_received': self.chunks_received,
            'transcription_updates': self.transcription_updates,
            'intent_updates': self.intent_updates
        }
