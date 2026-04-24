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


def _preprocess_audio(audio_array, sr: int = 16000) -> bytes:
    """
    Preprocess audio for better Whisper detection
    - Normalize volume
    - Remove silence/noise
    - Ensure proper format
    """
    import numpy as np
    
    if audio_array is None or len(audio_array) == 0:
        return b''
    
    # Normalize audio (boost quiet audio)
    max_val = np.max(np.abs(audio_array))
    if max_val > 0:
        audio_array = audio_array / max_val  # Normalize to -1 to 1
    
    # Apply simple noise gate - remove very quiet parts
    threshold = 0.02
    audio_array[np.abs(audio_array) < threshold] = 0
    
    # Boost volume if too quiet
    mean_val = np.mean(np.abs(audio_array[audio_array != 0]))
    if mean_val < 0.1:
        audio_array = audio_array * 2
    
    # Convert to 16-bit PCM
    pcm_int16 = np.clip(audio_array * 32767, -32768, 32767).astype(np.int16)
    return pcm_int16.tobytes()


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
                
                # Try different strategies to load audio
                audio_array = None
                
                # Strategy 1: Check if it's a recognized format (WAV, MP3, WebM)
                if _is_wav_file(audio_data):
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
                if audio_array is None:
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
            
            # Log audio levels for debugging
            import numpy as np
            max_level = float(np.max(np.abs(audio_array)))
            mean_level = float(np.mean(np.abs(audio_array)))
            logger.info(f"Audio levels - Max: {max_level:.4f}, Mean: {mean_level:.6f}")
            
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
            
            # If no speech detected, return empty but don't fail
            if not text:
                logger.warning(f"No speech detected in audio (levels: max={max_level:.4f}, mean={mean_level:.6f})")
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
            'success': bool
        }
    """
    try:
        engine = get_stt_engine()
        text, lang, confidence = engine.transcribe(
            audio_file,
            language=language,
            translate_to_english=translate_to_english
        )
        return {
            'text': text,
            'language': lang,
            'confidence': float(confidence),
            'success': True
        }
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return {
            'text': '',
            'language': 'unknown',
            'confidence': 0.0,
            'success': False,
            'error': str(e)
        }
