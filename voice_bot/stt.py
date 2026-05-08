"""
Speech-to-Text module using OpenAI Whisper

Features:
- Load model once (singleton pattern)
- Multilingual support with automatic translation to English
- Error handling and logging
- Efficient audio processing
"""

import logging
import io
import wave
from typing import Tuple, Optional
import warnings

logger = logging.getLogger(__name__)

# Suppress Whisper model warnings
warnings.filterwarnings('ignore')


def _is_wav_file(data: bytes) -> bool:
    """Check if bytes data is a WAV file (has RIFF header)"""
    return len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WAVE'


def _is_webm_file(data: bytes) -> bool:
    """Check if bytes data is a WebM file"""
    return len(data) >= 4 and data[:4] == b'\x1aEL\xdf'


def _is_mp3_file(data: bytes) -> bool:
    """Check if bytes data is an MP3 file"""
    return len(data) >= 2 and (data[:2] == b'ID' or data[:2] == b'\xff\xfb' or data[:2] == b'\xff\xfa')


def _int16_bytes_to_float32(data: bytes) -> Tuple[any, int]:
    """
    CRITICAL FIX: Convert raw Int16 PCM bytes to Float32 numpy array
    
    This is the key function for fixing "No speech detected" issues.
    Properly handles:
    - Little-endian byte order (from browser)
    - Int16 to Float32 conversion (-1.0 to 1.0 range)
    - Sample rate validation
    
    Args:
        data: Raw bytes (Int16 PCM format)
    
    Returns:
        Tuple of (audio_array_float32, sample_rate)
    """
    import numpy as np
    
    if not data or len(data) < 2:
        logger.error("Invalid audio data: empty or too short")
        return None, 16000
    
    try:
        # CRITICAL: Use '<i2' for little-endian int16
        # This matches browser's byte order (Little Endian)
        audio_int16 = np.frombuffer(data, dtype='<i2')  # Little-endian int16
        
        # CRITICAL: Convert Int16 to Float32 in range -1.0 to 1.0
        # Use proper scaling: divide by 32768 (2^15)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        logger.info(f"Converted {len(data)} bytes → {len(audio_float32)} samples (Int16 PCM → Float32)")
        logger.debug(f"Audio range after conversion: min={np.min(audio_float32):.6f}, max={np.max(audio_float32):.6f}, mean={np.mean(audio_float32):.6f}")
        
        return audio_float32, 16000
        
    except Exception as e:
        logger.error(f"Failed to convert Int16 bytes to Float32: {e}")
        return None, 16000


def _preprocess_audio(audio_array, sr: int = 16000):
    """
    Preprocess audio for better Whisper detection
    - Handle clipped/saturated audio with aggressive recovery
    - Normalize volume
    - Remove silence/noise
    - Boost speech frequencies
    """
    import numpy as np
    
    if audio_array is None or len(audio_array) == 0:
        return audio_array
    
    audio_array = audio_array.astype(np.float32)
    original_max = np.max(np.abs(audio_array))
    
    # ===== STEP 1: Detect and recover clipped audio =====
    is_clipped = original_max >= 0.98
    
    if is_clipped:
        logger.warning(f"Audio clipped at max: {original_max:.4f}. Applying aggressive recovery...")
        
        # Strategy 1: Remove clipping by applying soft expansion
        # This reconstructs clipped peaks (approximately)
        clipping_threshold = 0.95
        clipped_mask = np.abs(audio_array) >= clipping_threshold
        
        if np.any(clipped_mask):
            # For clipped regions, apply inverse tanh to expand them back
            # This roughly reconstructs what was clipped
            clipped_samples = audio_array[clipped_mask]
            # Scale down first to expand, scale back up
            expanded = np.sign(clipped_samples) * (1.0 + 0.5 * (np.abs(clipped_samples) - clipping_threshold))
            audio_array[clipped_mask] = expanded
            logger.info(f"Recovered {np.sum(clipped_mask)} clipped samples")
        
        # Strategy 2: Apply gentle saturation recovery
        # Reduce overall level to give room for peaks
        audio_array = audio_array * 0.8
    
    # ===== STEP 2: Normalize audio =====
    # After any transformations, normalize to safe level
    current_max = np.max(np.abs(audio_array))
    if current_max > 0:
        # Normalize to 0.8 (leave headroom for Whisper)
        audio_array = (audio_array / current_max) * 0.8
    
    # ===== STEP 3: Remove DC offset with high-pass filter =====
    from scipy import signal
    try:
        # High-pass filter to remove DC and very low frequencies
        # Speech is typically 80-20000 Hz, so 50Hz cutoff is safe
        sos = signal.butter(4, 50, 'hp', fs=sr, output='sos')
        audio_array = signal.sosfilt(sos, audio_array)
        logger.debug("Applied high-pass filter")
    except Exception as e:
        logger.debug(f"High-pass filter skipped: {e}")
    
    # ===== STEP 4: Adaptive noise gate =====
    # Remove very quiet parts while preserving speech
    rms = np.sqrt(np.mean(audio_array ** 2))
    
    # Adaptive threshold: scale based on signal level
    if rms > 0:
        # Threshold is 5% of RMS, minimum 0.01
        threshold = max(0.01, rms * 0.05)
    else:
        threshold = 0.01
    
    quiet_mask = np.abs(audio_array) < threshold
    audio_array[quiet_mask] = 0
    logger.debug(f"Applied noise gate: threshold={threshold:.4f}, removed {np.sum(quiet_mask)} samples")
    
    # ===== STEP 5: Boost speech if too quiet =====
    # Calculate RMS of non-zero samples
    nonzero_samples = audio_array[audio_array != 0]
    if len(nonzero_samples) > 0:
        mean_val = np.mean(np.abs(nonzero_samples))
        
        if mean_val < 0.10:  # Very quiet
            logger.info(f"Audio very quiet (mean: {mean_val:.4f}), boosting 3x")
            audio_array = audio_array * 3.0
        elif mean_val < 0.15:  # Somewhat quiet
            logger.info(f"Audio quiet (mean: {mean_val:.4f}), boosting 2x")
            audio_array = audio_array * 2.0
        elif mean_val < 0.25:  # Moderately quiet
            logger.debug(f"Audio moderate (mean: {mean_val:.4f}), boosting 1.5x")
            audio_array = audio_array * 1.5
    
    # ===== STEP 6: Ensure bounds =====
    audio_array = np.clip(audio_array, -1.0, 1.0)
    
    final_max = np.max(np.abs(audio_array))
    final_mean = np.mean(np.abs(audio_array))
    logger.debug(f"Preprocessing complete - Original max: {original_max:.4f}, Final max: {final_max:.4f}, Final mean: {final_mean:.6f}")
    
    return audio_array


def _extract_raw_pcm_from_webm(blob_data: bytes) -> Optional[bytes]:
    """
    Try to extract raw PCM data from a MediaRecorder blob (WebM, MP3, etc.)
    
    Args:
        blob_data: Raw blob data from MediaRecorder
    
    Returns:
        Raw PCM bytes or None if extraction fails
    """
    try:
        import soundfile as sf
        import numpy as np
        
        # soundfile can handle WebM, MP3, and other formats
        try:
            data, sr = sf.read(io.BytesIO(blob_data))
            logger.info(f"Extracted PCM from blob using soundfile: {len(data)} samples @ {sr} Hz")
            
            # Resample to 16000 Hz if needed
            if sr != 16000:
                import librosa
                data = librosa.resample(data, orig_sr=sr, target_sr=16000)
                logger.info(f"Resampled to 16000 Hz: {len(data)} samples")
            
            # Ensure mono
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            
            # Convert to 16-bit PCM bytes
            pcm_int16 = np.clip(data * 32767, -32768, 32767).astype(np.int16)
            return pcm_int16.tobytes()
        
        except Exception as sf_error:
            logger.debug(f"Soundfile extraction failed: {type(sf_error).__name__}: {sf_error}")
            return None
    
    except ImportError:
        logger.debug("soundfile not available for blob extraction")
        return None
    except Exception as e:
        logger.debug(f"Failed to extract PCM from blob: {e}")
        return None


def _raw_pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, 
                    sample_width: int = 2) -> io.BytesIO:
    """
    Convert raw PCM audio data to WAV format
    
    Args:
        pcm_data: Raw PCM bytes
        sample_rate: Sampling rate in Hz (default 16000)
        channels: Number of channels (default 1 for mono)
        sample_width: Sample width in bytes (default 2 for 16-bit)
    
    Returns:
        BytesIO object containing WAV-formatted audio
    """
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    
    wav_buffer.seek(0)
    return wav_buffer


class WhisperSTTEngine:
    """Singleton class for Whisper speech-to-text engine"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the engine (lazy load model on first use)"""
        self.model_size = 'base'  # Options: tiny, base, small, medium, large
        self.device = 'cpu'  # Use 'cuda' for GPU
    
    def _load_model(self):
        """Load Whisper model on first use (lazy loading)"""
        if self._model is None:
            try:
                import whisper
                logger.info(f"Loading Whisper {self.model_size} model...")
                self._model = whisper.load_model(self.model_size, device=self.device)
                logger.info(f"Whisper model loaded successfully on {self.device}")
            except ImportError:
                logger.error("Whisper not installed. Install with: pip install openai-whisper")
                raise
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {str(e)}")
                raise
    
    def transcribe(
        self,
        audio_file,
        language: str = 'en',
        translate_to_english: bool = True
    ) -> Tuple[str, str, float]:
        """
        Transcribe audio file to text
        
        Args:
            audio_file: File-like object, bytes, or path to audio file
            language: Language code (e.g., 'en', 'es', 'hi')
            translate_to_english: Whether to translate non-English to English
        
        Returns:
            Tuple of (transcribed_text, detected_language, confidence_score)
        
        Raises:
            ValueError: If audio is invalid or empty
            RuntimeError: If transcription fails
        """
        try:
            # Load model if not already loaded
            if self._model is None:
                self._load_model()
            
            # Convert BytesIO or bytes to numpy array using librosa
            import librosa
            import numpy as np
            
            # Handle different input types
            if isinstance(audio_file, bytes):
                audio_file = io.BytesIO(audio_file)
            
            if hasattr(audio_file, 'read'):
                # It's a file-like object (BytesIO, file handle, etc.)
                audio_file.seek(0)  # Reset position to start
                audio_data = audio_file.read()
                
                if not audio_data:
                    raise ValueError("Audio file is empty or invalid")
                
                logger.info(f"Audio data size: {len(audio_data)} bytes")
                
                # Detect audio format
                format_detected = "unknown"
                
                # CRITICAL FIX: Check for raw Int16 PCM FIRST
                # Raw PCM from browser is just Int16 bytes, no header
                # Most likely if:
                # 1. Exact multiple of 2 (each sample is 2 bytes)
                # 2. Not a standard format (no WAV/WebM/MP3 header)
                # 3. Size suggests normal speech (100-100k samples reasonable)
                is_raw_pcm = (len(audio_data) % 2 == 0 and 
                             not _is_wav_file(audio_data) and 
                             not _is_webm_file(audio_data) and 
                             not _is_mp3_file(audio_data) and
                             len(audio_data) >= 4)  # At least 2 samples
                
                if is_raw_pcm:
                    format_detected = "Raw_PCM_Int16"
                    logger.info("Detected format: Raw PCM Int16 (from browser)")
                    audio_array, sr = _int16_bytes_to_float32(audio_data)
                    if audio_array is not None:
                        logger.info(f"Successfully loaded raw PCM: {len(audio_array)} samples @ {sr}Hz")
                    else:
                        audio_array = None
                
                # Try standard formats if raw PCM didn't work
                if audio_array is None:
                    if _is_wav_file(audio_data):
                        format_detected = "WAV"
                    elif _is_webm_file(audio_data):
                        format_detected = "WebM"
                    elif _is_mp3_file(audio_data):
                        format_detected = "MP3"
                    else:
                        format_detected = "raw/unknown"
                
                logger.info(f"Detected format: {format_detected}")
                
                # Try different strategies to load audio
                # Note: audio_array may already be set from raw PCM detection above
                
                # Strategy 1: Check if it's a recognized format (WAV, MP3, WebM)
                if audio_array is None and format_detected == "WAV":
                    logger.info("WAV file detected, loading with librosa")
                    try:
                        audio_array, sr = librosa.load(
                            io.BytesIO(audio_data),
                            sr=16000,
                            mono=True
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load as WAV: {e}")
                        audio_array = None
                
                # Strategy 2: Try to extract PCM from MediaRecorder blob (WebM, MP3, etc)
                if audio_array is None and format_detected in ["WebM", "MP3", "raw/unknown"]:
                    logger.info("Trying to extract PCM from blob...")
                    pcm_data = _extract_raw_pcm_from_webm(audio_data)
                    if pcm_data:
                        logger.info(f"PCM extracted: {len(pcm_data)} bytes")
                        try:
                            audio_array, sr = librosa.load(
                                io.BytesIO(_raw_pcm_to_wav(pcm_data, 16000, 1, 2).read()),
                                sr=16000,
                                mono=True
                            )
                            logger.info(f"Successfully loaded extracted PCM: {len(audio_array)} samples")
                        except Exception as e:
                            logger.warning(f"Failed to load extracted PCM: {e}")
                            audio_array = None
                
                # Strategy 3: Assume raw PCM at 16000 Hz, 16-bit, mono
                if audio_array is None:
                    logger.info("Treating audio as raw PCM...")
                    try:
                        audio_array, sr = librosa.load(
                            io.BytesIO(_raw_pcm_to_wav(audio_data, 16000, 1, 2).read()),
                            sr=16000,
                            mono=True
                        )
                        logger.info(f"Successfully loaded as raw PCM: {len(audio_array)} samples")
                    except Exception as e:
                        logger.warning(f"Failed to load as raw PCM: {e}")
                        audio_array = None
                
                if audio_array is None:
                    raise ValueError("Could not load audio in any format")
                
                # Convert to float32 (required by Whisper)
                audio_array = audio_array.astype(np.float32)
            
            elif isinstance(audio_file, str):
                # File path - load with librosa
                audio_array, sr = librosa.load(
                    audio_file,
                    sr=16000,
                    mono=True
                )
                audio_array = audio_array.astype(np.float32)
            
            else:
                raise ValueError(f"Unsupported audio type: {type(audio_file)}")
            
            # Validate audio array
            if audio_array is None or len(audio_array) == 0:
                raise ValueError("Failed to load audio data")
            
            logger.info(f"Audio loaded: {len(audio_array)} samples @ 16kHz")
            
            # Log audio levels BEFORE preprocessing for debugging
            import numpy as np
            max_level_before = float(np.max(np.abs(audio_array)))
            mean_level_before = float(np.mean(np.abs(audio_array)))
            logger.info(f"Audio levels (BEFORE processing) - Max: {max_level_before:.4f}, Mean: {mean_level_before:.6f}")
            
            # Detect clipping before preprocessing
            audio_is_clipped = max_level_before >= 0.98
            
            # CRITICAL: Check if audio is completely saturated/unrecoverable
            clipped_samples = np.sum(np.abs(audio_array) >= 0.99)
            total_samples = len(audio_array)
            clipping_ratio = clipped_samples / total_samples if total_samples > 0 else 0
            
            if clipping_ratio > 0.5:
                logger.warning(f"⚠️  SEVERE CLIPPING: {clipping_ratio*100:.1f}% of audio is saturated - possibly UNRECOVERABLE")
                if clipping_ratio > 0.9:
                    logger.error(f"❌ Audio completely saturated ({clipping_ratio*100:.1f}% clipped) - user needs to lower microphone gain immediately")
            
            # Preprocess audio to handle clipping and improve detection
            audio_array = _preprocess_audio(audio_array, sr=16000)
            
            # Log audio levels AFTER preprocessing
            max_level_after = float(np.max(np.abs(audio_array)))
            mean_level_after = float(np.mean(np.abs(audio_array)))
            logger.info(f"Audio levels (AFTER preprocessing) - Max: {max_level_after:.4f}, Mean: {mean_level_after:.6f}")
            
            if max_level_before >= 0.99:
                logger.warning(f"⚠️  CLIPPED AUDIO DETECTED - Original max: {max_level_before:.4f} → Recovered to: {max_level_after:.4f}")
            
            # Ensure float32 for Whisper
            audio_array = audio_array.astype(np.float32)
            
            # Transcribe with translation option (with preprocessing)
            task = 'translate' if translate_to_english else 'transcribe'
            
            # Try transcription
            try:
                result = self._model.transcribe(
                    audio_array,
                    task=task,
                    language=language if language != 'auto' else None,
                    fp16=False,  # Set to True if using GPU
                    verbose=False
                )
            except Exception as whisper_error:
                logger.error(f"Whisper transcription error: {whisper_error}")
                raise RuntimeError(f"Transcription failed: {str(whisper_error)}")
            
            # Extract results
            text = result.get('text', '').strip()
            detected_lang = result.get('language', 'en')
            confidence = result.get('confidence', 0.0)
            
            # Log what we got
            logger.info(f"Whisper result: text_len={len(text)}, lang={detected_lang}, confidence={confidence}")
            
            # If no speech detected, provide detailed diagnostics
            if not text:
                logger.warning(f"No speech detected in audio (levels: max={max_level_before:.4f}, mean={mean_level_before:.6f})")
                
                # Check clipping severity for diagnostics
                if clipping_ratio > 0.8:
                    logger.critical(
                        f"❌ CRITICAL: Audio is {clipping_ratio*100:.1f}% clipped. "
                        f"Whisper cannot extract speech from completely saturated audio. "
                        f"User MUST lower microphone input gain immediately."
                    )
                elif clipping_ratio > 0.5:
                    logger.error(
                        f"⚠️ SEVERE: Audio is {clipping_ratio*100:.1f}% clipped. "
                        f"Speech reconstruction attempted but may fail. "
                        f"Recommend user lower microphone gain."
                    )
                
                return "", detected_lang, 0.0
            
            logger.info(
                f"Transcription successful: {len(text)} chars, "
                f"language: {detected_lang}, confidence: {confidence:.2f}"
            )
            
            return text, detected_lang, confidence
        
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to transcribe audio: {str(e)}")
    
    def get_model_info(self) -> dict:
        """Get information about loaded model"""
        return {
            'model_size': self.model_size,
            'device': self.device,
            'loaded': self._model is not None
        }


# Global instance
_stt_engine = None


def get_stt_engine() -> WhisperSTTEngine:
    """Get or create the singleton Whisper engine"""
    global _stt_engine
    if _stt_engine is None:
        _stt_engine = WhisperSTTEngine()
    return _stt_engine


def transcribe_audio(
    audio_file,
    language: str = 'en',
    translate_to_english: bool = True
) -> dict:
    """
    Convenience function to transcribe audio
    
    Returns:
        {
            'text': transcribed text,
            'language': detected language code,
            'confidence': confidence score,
            'success': bool,
            'audio_clipped': bool,  # True if input audio was clipped/saturated
            'error': str (optional)
        }
    """
    try:
        engine = get_stt_engine()
        
        # Check for clipping in the raw audio before transcription
        audio_clipped = False
        if isinstance(audio_file, bytes):
            # Try to estimate audio levels from raw data
            import numpy as np
            try:
                audio_data = audio_file
                # Convert raw PCM to float for level checking
                pcm_int16 = np.frombuffer(audio_data[:4000], dtype=np.int16)  # First 2 seconds
                float_audio = pcm_int16.astype(np.float32) / 32768.0
                max_level = np.max(np.abs(float_audio))
                audio_clipped = max_level >= 0.98
            except Exception as e:
                logger.debug(f"Could not check audio clipping: {e}")
        
        text, lang, confidence = engine.transcribe(
            audio_file,
            language=language,
            translate_to_english=translate_to_english
        )
        return {
            'text': text,
            'language': lang,
            'confidence': float(confidence),
            'success': True,
            'audio_clipped': audio_clipped
        }
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return {
            'text': '',
            'language': 'unknown',
            'confidence': 0.0,
            'success': False,
            'audio_clipped': False,
            'error': str(e)
        }
