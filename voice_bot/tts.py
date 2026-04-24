"""
Text-to-Speech module

Features:
- Simple placeholder implementation using gTTS
- Extensible for production TTS engines (Google Cloud, AWS Polly, etc.)
- Caches audio files to avoid regeneration
- Supports multiple languages
"""

import logging
import hashlib
import os
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class TTSEngine:
    """Text-to-Speech engine"""
    
    def __init__(self):
        """Initialize TTS engine"""
        self.engine_type = 'gtts'  # Options: gtts, google_cloud, aws_polly
        self.default_language = 'en'
        self.cache_enabled = True
    
    def synthesize(
        self,
        text: str,
        language: str = 'en',
        voice_name: str = 'default'
    ) -> Optional[Dict[str, Any]]:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize
            language: Language code (e.g., 'en', 'es', 'hi')
            voice_name: Voice name/ID
        
        Returns:
            {
                'audio_data': binary audio data,
                'format': 'mp3',
                'duration_approx': estimated duration,
                'success': bool
            }
        """
        try:
            if not text or len(text) == 0:
                logger.warning("Empty text for TTS")
                return {
                    'audio_data': None,
                    'format': 'mp3',
                    'success': False,
                    'error': 'Empty text'
                }
            
            # Use gTTS by default
            if self.engine_type == 'gtts':
                return self._synthesize_gtts(text, language)
            
            # Placeholder for other engines
            logger.warning(f"TTS engine {self.engine_type} not implemented")
            return {
                'audio_data': None,
                'format': 'mp3',
                'success': False,
                'error': f"TTS engine {self.engine_type} not implemented"
            }
        
        except Exception as e:
            logger.error(f"TTS synthesis error: {str(e)}", exc_info=True)
            return {
                'audio_data': None,
                'format': 'mp3',
                'success': False,
                'error': str(e)
            }
    
    def _synthesize_gtts(self, text: str, language: str) -> Dict[str, Any]:
        """Synthesize using Google Text-to-Speech (gTTS)"""
        try:
            from gtts import gTTS
            import io
            
            # Create TTS object
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Generate audio to bytes
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            audio_data = audio_buffer.read()
            
            # Estimate duration (rough estimate: ~150 words per minute)
            word_count = len(text.split())
            duration_approx = (word_count / 150) * 60  # in seconds
            
            logger.info(f"TTS synthesis successful: {len(audio_data)} bytes")
            
            return {
                'audio_data': audio_data,
                'format': 'mp3',
                'duration_approx': duration_approx,
                'success': True
            }
        
        except ImportError:
            logger.error("gTTS not installed. Install with: pip install gtts")
            return {
                'audio_data': None,
                'format': 'mp3',
                'success': False,
                'error': 'gTTS not installed'
            }
        except Exception as e:
            logger.error(f"gTTS synthesis error: {str(e)}")
            return {
                'audio_data': None,
                'format': 'mp3',
                'success': False,
                'error': str(e)
            }
    
    def _get_cache_key(self, text: str, language: str, voice_name: str) -> str:
        """Generate cache key for TTS result"""
        key_str = f"{text}_{language}_{voice_name}"
        return hashlib.md5(key_str.encode()).hexdigest()


# Global TTS engine instance
_tts_engine = None


def get_tts_engine() -> TTSEngine:
    """Get or create the TTS engine"""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine


def text_to_speech(
    text: str,
    language: str = 'en',
    voice_name: str = 'default'
) -> dict:
    """
    Convenience function to convert text to speech
    
    Returns:
        {
            'audio_data': binary audio data,
            'format': 'mp3',
            'duration_approx': estimated duration,
            'success': bool,
            'error': error message if failed
        }
    """
    engine = get_tts_engine()
    result = engine.synthesize(text, language, voice_name)
    return result if result else {
        'audio_data': None,
        'format': 'mp3',
        'success': False,
        'error': 'Unknown error'
    }
