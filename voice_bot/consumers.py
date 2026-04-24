"""
WebSocket Consumer for Real-Time Voice Streaming

Features:
- Accept audio chunks via WebSocket
- Process in real-time
- Send live transcription updates
- Intent classification as it progresses
- Streaming response generation
"""

import logging
import asyncio
import json
import time
import uuid
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async

from django.contrib.auth.models import User
from .models import VoiceQuery, VoiceQueryLog
from .stt import get_stt_engine
from .intent import get_classifier
from .services import get_service_handler
from .tts import get_tts_engine

logger = logging.getLogger(__name__)


class VoiceStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time voice streaming
    
    Handles:
    - Audio chunk reception
    - Live transcription
    - Real-time intent detection
    - Streaming responses
    """
    
    async def connect(self):
        """Accept WebSocket connection"""
        self.user = self.scope['user']
        self.session_id = str(uuid.uuid4())
        self.audio_chunks = []
        self.transcribed_text = ""
        self.current_intent = None
        self.start_time = time.time()
        
        # Store connection metadata
        self.language = 'en'
        self.include_tts = False
        
        # Processing state
        self.is_processing = False
        self.stt_engine = None
        self.classifier = None
        self.service_handler = None
        
        await self.accept()
        
        logger.info(f"[{self.session_id}] WebSocket connected - User: {self.user.username if self.user.is_authenticated else 'Anonymous'}")
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat()
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"[{self.session_id}] WebSocket disconnected - Close code: {close_code}")
        
        # Save session data if we have meaningful data
        if self.transcribed_text or self.current_intent:
            await self._save_voice_query_async()
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Receive messages from client
        
        Message types:
        - {'type': 'init', 'language': 'en', 'include_tts': true}
        - {'type': 'audio_chunk', 'data': base64_audio}
        - {'type': 'process', 'final': true}
        - {'type': 'stop'}
        """
        try:
            if text_data:
                data = json.loads(text_data)
                message_type = data.get('type')
                
                if message_type == 'init':
                    await self._handle_init(data)
                
                elif message_type == 'audio_chunk':
                    await self._handle_audio_chunk(data)
                
                elif message_type == 'process':
                    await self._handle_process(data)
                
                elif message_type == 'stop':
                    await self._handle_stop()
                
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': f'Unknown message type: {message_type}'
                    }))
            
            elif bytes_data:
                # Raw binary audio chunk
                await self._handle_audio_bytes(bytes_data)
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"[{self.session_id}] Error receiving message: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Processing error: {str(e)}'
            }))
    
    # ========== MESSAGE HANDLERS ==========
    
    async def _handle_init(self, data):
        """Initialize streaming session"""
        self.language = data.get('language', 'en')
        self.include_tts = data.get('include_tts', False)
        
        # Initialize processing engines
        self.stt_engine = await sync_to_async(lambda: get_stt_engine())()
        self.classifier = await sync_to_async(lambda: get_classifier())()
        self.service_handler = await sync_to_async(lambda: get_service_handler())()
        
        logger.info(f"[{self.session_id}] Session initialized - Language: {self.language}")
        
        await self.send(text_data=json.dumps({
            'type': 'session_ready',
            'message': 'Ready to receive audio'
        }))
    
    async def _handle_audio_chunk(self, data):
        """Handle audio chunk"""
        try:
            # Decode base64 audio
            import base64
            audio_data = base64.b64decode(data.get('data', ''))
            
            if not audio_data:
                return
            
            self.audio_chunks.append(audio_data)
            
            # Send chunk acknowledgment
            await self.send(text_data=json.dumps({
                'type': 'chunk_received',
                'chunk_index': len(self.audio_chunks),
                'total_bytes': sum(len(c) for c in self.audio_chunks)
            }))
            
            # Auto-process chunks after receiving 2 chunks (4+ seconds of audio)
            # This ensures we have enough audio for reliable transcription
            if len(self.audio_chunks) >= 2 and len(self.audio_chunks) % 2 == 0:
                await self._process_partial_audio()
        
        except Exception as e:
            logger.error(f"[{self.session_id}] Error handling audio chunk: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Audio processing error: {str(e)}'
            }))
    
    async def _handle_audio_bytes(self, bytes_data):
        """Handle raw binary audio data"""
        self.audio_chunks.append(bytes_data)
        await self.send(text_data=json.dumps({
            'type': 'chunk_received',
            'bytes': len(bytes_data)
        }))
    
    async def _handle_process(self, data):
        """Process accumulated audio"""
        is_final = data.get('final', True)
        
        logger.info(f"[{self.session_id}] Processing audio - Final: {is_final}")
        
        await self._process_audio_final(is_final)
    
    async def _handle_stop(self):
        """Stop and finalize"""
        await self._process_audio_final(is_final=True)
        logger.info(f"[{self.session_id}] Stream stopped by client")
    
    # ========== AUDIO PROCESSING ==========
    
    async def _process_partial_audio(self):
        """Process accumulated audio partially (for progress updates)"""
        if not self.audio_chunks or self.is_processing:
            return
        
        self.is_processing = True
        
        try:
            # Combine audio chunks
            audio_data = b''.join(self.audio_chunks)
            
            # Need at least ~32KB for 2 seconds of audio (at 16000 Hz, 16-bit, mono)
            if len(audio_data) < 32000:
                self.is_processing = False
                return
            
            # Send processing indicator
            await self.send(text_data=json.dumps({
                'type': 'processing_started',
                'bytes': len(audio_data),
                'chunks': len(self.audio_chunks)
            }))
            
            # Try to transcribe asynchronously (don't fail if it doesn't work on partial audio)
            try:
                transcript_result = await sync_to_async(self._transcribe_sync)(
                    audio_data,
                    self.language
                )
                
                if transcript_result['success'] and transcript_result['text']:
                    self.transcribed_text = transcript_result['text']
                    
                    # Send partial transcription
                    await self.send(text_data=json.dumps({
                        'type': 'partial_transcript',
                        'text': self.transcribed_text,
                        'confidence': transcript_result['confidence'],
                        'language': transcript_result['language']
                    }))
                    
                    # Classify intent
                    intent_result = await sync_to_async(self._classify_sync)(
                        self.transcribed_text
                    )
                    
                    self.current_intent = intent_result['intent']
                    
                    # Send intent update
                    await self.send(text_data=json.dumps({
                        'type': 'intent_detected',
                        'intent': intent_result['intent'],
                        'confidence': intent_result['confidence'],
                        'candidates': intent_result['candidates']
                    }))
                else:
                    # Transcription didn't yield results, just log silently
                    logger.debug(f"[{self.session_id}] No text transcribed from partial audio yet")
            
            except Exception as transcribe_error:
                # Don't fail the partial processing - just log and continue
                # This is expected with partial MediaRecorder chunks
                logger.debug(f"[{self.session_id}] Partial transcription skipped: {str(transcribe_error)}")
                await self.send(text_data=json.dumps({
                    'type': 'status_update',
                    'message': f'Received {len(self.audio_chunks)} chunks ({len(audio_data)} bytes), waiting for more...'
                }))
        
        except Exception as e:
            logger.error(f"[{self.session_id}] Partial processing error: {str(e)}")
            # Don't send error to client - just log it
        
        finally:
            self.is_processing = False
    
    async def _process_audio_final(self, is_final=True):
        """Process final audio and generate response"""
        if not self.audio_chunks:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'No audio data'
            }))
            return
        
        if self.is_processing:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Still processing previous audio'
            }))
            return
        
        self.is_processing = True
        processing_start = time.time()
        
        try:
            # Combine all audio chunks
            audio_data = b''.join(self.audio_chunks)
            
            await self.send(text_data=json.dumps({
                'type': 'final_processing_started',
                'bytes': len(audio_data)
            }))
            
            # Final transcription
            transcript_result = await sync_to_async(self._transcribe_sync)(
                audio_data,
                self.language
            )
            
            if not transcript_result['success']:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f"Transcription failed: {transcript_result.get('error')}"
                }))
                return
            
            # Handle case where transcription succeeded but no speech was detected
            self.transcribed_text = transcript_result['text'].strip()
            
            if not self.transcribed_text:
                # No speech detected - still send result with empty text
                logger.warning(f"[{self.session_id}] No speech detected in final audio")
                await self.send(text_data=json.dumps({
                    'type': 'final_result',
                    'detected_text': '',
                    'detected_language': transcript_result.get('language', 'en'),
                    'intent': 'UNKNOWN',
                    'confidence': 0.0,
                    'response': 'I could not understand any speech. Please try again.',
                    'data': {},
                    'processing_time_ms': int((time.time() - processing_start) * 1000)
                }))
                return
            
            # Final intent classification
            intent_result = await sync_to_async(self._classify_sync)(
                self.transcribed_text
            )
            
            self.current_intent = intent_result['intent']
            
            # Get service response
            service_result = await sync_to_async(self._service_handler_sync)(
                intent_result['intent'],
                self.transcribed_text
            )
            
            response_text = service_result.get('response', '')
            response_data = service_result.get('data', {})
            
            # Send final result
            await self.send(text_data=json.dumps({
                'type': 'final_result',
                'detected_text': self.transcribed_text,
                'detected_language': transcript_result['language'],
                'intent': intent_result['intent'],
                'confidence': intent_result['confidence'],
                'response': response_text,
                'data': response_data,
                'processing_time_ms': int((time.time() - processing_start) * 1000)
            }))
            
            # Generate TTS response if requested
            if self.include_tts and response_text:
                await self._generate_tts_streaming(response_text)
            
            # Save to database
            await self._save_voice_query_async(
                transcript_result, intent_result, service_result, 
                int((time.time() - processing_start) * 1000)
            )
        
        except Exception as e:
            logger.error(f"[{self.session_id}] Final processing error: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Processing failed: {str(e)}'
            }))
        
        finally:
            self.is_processing = False
            self.audio_chunks = []  # Clear for next stream
    
    # ========== TTS STREAMING ==========
    
    async def _generate_tts_streaming(self, text):
        """Generate and stream TTS audio"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'tts_generating',
                'message': 'Generating audio response...'
            }))
            
            tts_result = await sync_to_async(self._tts_sync)(text)
            
            if tts_result['success'] and tts_result.get('audio_data'):
                # Stream audio in chunks
                import base64
                audio_b64 = base64.b64encode(tts_result['audio_data']).decode('utf-8')
                
                await self.send(text_data=json.dumps({
                    'type': 'tts_response',
                    'audio': audio_b64,
                    'format': 'mp3',
                    'duration_approx': tts_result.get('duration_approx', 0)
                }))
            else:
                logger.warning(f"[{self.session_id}] TTS generation failed")
        
        except Exception as e:
            logger.error(f"[{self.session_id}] TTS error: {str(e)}")
    
    # ========== SYNC WRAPPERS ==========
    
    def _transcribe_sync(self, audio_data, language):
        """Sync wrapper for transcription"""
        try:
            import io
            text, lang, confidence = self.stt_engine.transcribe(
                io.BytesIO(audio_data),
                language=language
            )
            return {
                'success': True,
                'text': text,
                'language': lang,
                'confidence': float(confidence)
            }
        except Exception as e:
            logger.error(f"[{self.session_id}] Transcription sync error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _classify_sync(self, text):
        """Sync wrapper for intent classification"""
        try:
            intent, confidence, candidates = self.classifier.classify(text)
            return {
                'intent': intent,
                'confidence': float(confidence),
                'candidates': candidates
            }
        except Exception as e:
            logger.error(f"[{self.session_id}] Classification sync error: {str(e)}")
            return {
                'intent': 'UNKNOWN',
                'confidence': 0.0,
                'candidates': []
            }
    
    def _service_handler_sync(self, intent, text):
        """Sync wrapper for service handler"""
        try:
            user = self.user if self.user.is_authenticated else None
            result = self.service_handler.handle_query(intent, text, user)
            return result
        except Exception as e:
            logger.error(f"[{self.session_id}] Service handler sync error: {str(e)}")
            return {
                'response': 'An error occurred processing your request',
                'data': {},
                'success': False
            }
    
    def _tts_sync(self, text):
        """Sync wrapper for TTS"""
        try:
            from .tts import text_to_speech
            result = text_to_speech(text, language=self.language)
            return result
        except Exception as e:
            logger.error(f"[{self.session_id}] TTS sync error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ========== DATABASE OPERATIONS ==========
    
    async def _save_voice_query_async(
        self, 
        transcript_result=None, 
        intent_result=None, 
        service_result=None,
        processing_time_ms=0
    ):
        """Save voice query to database asynchronously"""
        try:
            user = self.user if self.user.is_authenticated else None
            
            await database_sync_to_async(VoiceQuery.objects.create)(
                user=user,
                session_id=self.session_id,
                transcribed_text=self.transcribed_text or '',
                detected_language=transcript_result.get('language', 'en') if transcript_result else 'en',
                intent=intent_result.get('intent', 'UNKNOWN') if intent_result else 'UNKNOWN',
                confidence_score=intent_result.get('confidence', 0) if intent_result else 0,
                response_message=service_result.get('response', '') if service_result else '',
                processing_time_ms=processing_time_ms
            )
            
            logger.info(f"[{self.session_id}] Query saved to database")
        
        except Exception as e:
            logger.error(f"[{self.session_id}] Error saving query: {str(e)}")
