#!/usr/bin/env python
"""
WebSocket Streaming Voice Bot - E2E Test Script

This script tests the complete real-time voice bot streaming functionality
including WebSocket connections, audio processing, and response generation.

Usage:
    python test_voice_bot_streaming.py
    python test_voice_bot_streaming.py --url ws://localhost:8000/ws/voice-stream/
    python test_voice_bot_streaming.py --audio path/to/audio.mp3
"""

import asyncio
import websockets
import json
import base64
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# Test configuration
TEST_CONFIG = {
    'ws_url': 'ws://localhost:8000/ws/voice-stream/',
    'language': 'en',
    'include_tts': False,
    'timeout': 30,
}

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.RESET}")

def print_data(label, value):
    print(f"  {label}: {Colors.BOLD}{value}{Colors.RESET}")

class VoiceBotStreamingTest:
    """Test suite for real-time voice bot streaming"""
    
    def __init__(self, ws_url, audio_file=None):
        self.ws_url = ws_url
        self.audio_file = audio_file
        self.session_id = None
        self.test_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        self.metrics = {
            'connection_time': 0,
            'session_init_time': 0,
            'first_chunk_time': 0,
            'final_result_time': 0,
            'total_time': 0,
            'chunks_sent': 0,
            'chunks_received': 0,
        }
    
    async def test_connection(self):
        """Test 1: WebSocket Connection"""
        print_header("Test 1: WebSocket Connection")
        try:
            start = time.time()
            async with websockets.connect(self.ws_url) as ws:
                self.metrics['connection_time'] = time.time() - start
                
                # Receive connection message
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                
                if data.get('type') == 'connection_established':
                    self.session_id = data.get('session_id')
                    print_success(f"Connected successfully")
                    print_data("Session ID", self.session_id[:8] + '...')
                    print_data("Connection Time", f"{self.metrics['connection_time']*1000:.1f}ms")
                    self.test_results['passed'].append("Connection")
                    return True
                else:
                    print_error(f"Unexpected response: {data}")
                    self.test_results['failed'].append("Connection")
                    return False
        except Exception as e:
            print_error(f"Connection failed: {str(e)}")
            self.test_results['failed'].append(f"Connection: {str(e)}")
            return False
    
    async def test_session_init(self):
        """Test 2: Session Initialization"""
        print_header("Test 2: Session Initialization")
        try:
            async with websockets.connect(self.ws_url) as ws:
                # Receive connection message
                await ws.recv()
                
                start = time.time()
                
                # Send init message
                await ws.send(json.dumps({
                    'type': 'init',
                    'language': TEST_CONFIG['language'],
                    'include_tts': TEST_CONFIG['include_tts']
                }))
                
                # Wait for session ready
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                
                self.metrics['session_init_time'] = time.time() - start
                
                if data.get('type') == 'session_ready':
                    print_success(f"Session initialized")
                    print_data("Init Time", f"{self.metrics['session_init_time']*1000:.1f}ms")
                    print_data("Language", TEST_CONFIG['language'])
                    print_data("Include TTS", TEST_CONFIG['include_tts'])
                    self.test_results['passed'].append("Session Init")
                    return True
                else:
                    print_error(f"Unexpected response: {data}")
                    self.test_results['failed'].append("Session Init")
                    return False
        except Exception as e:
            print_error(f"Session initialization failed: {str(e)}")
            self.test_results['failed'].append(f"Session Init: {str(e)}")
            return False
    
    async def test_audio_chunk_reception(self):
        """Test 3: Audio Chunk Reception"""
        print_header("Test 3: Audio Chunk Reception")
        try:
            async with websockets.connect(self.ws_url) as ws:
                # Initialize
                await ws.recv()  # connection
                await ws.send(json.dumps({
                    'type': 'init',
                    'language': TEST_CONFIG['language'],
                    'include_tts': False
                }))
                await ws.recv()  # session_ready
                
                # Send test audio chunk
                test_audio = base64.b64encode(b'\x00' * 1024).decode('utf-8')
                
                start = time.time()
                await ws.send(json.dumps({
                    'type': 'audio_chunk',
                    'data': test_audio
                }))
                
                # Receive chunk acknowledgment
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                
                self.metrics['first_chunk_time'] = time.time() - start
                
                if data.get('type') == 'chunk_received':
                    print_success(f"Audio chunk received and acknowledged")
                    print_data("Chunk Index", data.get('chunk_index'))
                    print_data("Total Bytes", data.get('total_bytes'))
                    print_data("Round Trip Time", f"{self.metrics['first_chunk_time']*1000:.1f}ms")
                    self.test_results['passed'].append("Audio Chunk Reception")
                    self.metrics['chunks_received'] += 1
                    return True
                else:
                    print_error(f"Unexpected response: {data}")
                    self.test_results['failed'].append("Audio Chunk Reception")
                    return False
        except Exception as e:
            print_error(f"Audio chunk test failed: {str(e)}")
            self.test_results['failed'].append(f"Audio Chunk: {str(e)}")
            return False
    
    async def test_partial_updates(self):
        """Test 4: Partial Transcription Updates"""
        print_header("Test 4: Partial Transcription Updates")
        try:
            async with websockets.connect(self.ws_url) as ws:
                # Initialize
                await ws.recv()  # connection
                await ws.send(json.dumps({
                    'type': 'init',
                    'language': TEST_CONFIG['language'],
                    'include_tts': False
                }))
                await ws.recv()  # session_ready
                
                # Send multiple audio chunks to trigger processing
                for i in range(60):  # Send enough chunks to trigger partial processing
                    test_audio = base64.b64encode(b'\x00' * 1024).decode('utf-8')
                    await ws.send(json.dumps({
                        'type': 'audio_chunk',
                        'data': test_audio
                    }))
                    
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1)
                        data = json.loads(msg)
                        
                        if data.get('type') == 'partial_transcript':
                            print_success(f"Partial transcription received")
                            print_data("Text", data.get('text', 'N/A')[:50])
                            print_data("Confidence", f"{data.get('confidence', 0):.2%}")
                            self.test_results['passed'].append("Partial Updates")
                            return True
                    except asyncio.TimeoutError:
                        pass
                
                print_info("Partial transcription not received (may need actual audio)")
                self.test_results['warnings'].append("Partial Updates not triggered")
                return True
        except Exception as e:
            print_error(f"Partial updates test failed: {str(e)}")
            self.test_results['failed'].append(f"Partial Updates: {str(e)}")
            return False
    
    async def test_final_processing(self):
        """Test 5: Final Processing"""
        print_header("Test 5: Final Processing")
        try:
            async with websockets.connect(self.ws_url) as ws:
                start_total = time.time()
                
                # Initialize
                await ws.recv()  # connection
                await ws.send(json.dumps({
                    'type': 'init',
                    'language': TEST_CONFIG['language'],
                    'include_tts': False
                }))
                await ws.recv()  # session_ready
                
                # Send audio chunks
                for i in range(10):
                    test_audio = base64.b64encode(b'\x00' * 2048).decode('utf-8')
                    await ws.send(json.dumps({
                        'type': 'audio_chunk',
                        'data': test_audio
                    }))
                    
                    try:
                        await asyncio.wait_for(ws.recv(), timeout=0.5)
                    except asyncio.TimeoutError:
                        pass
                
                # Trigger processing
                await ws.send(json.dumps({
                    'type': 'process',
                    'final': True
                }))
                
                # Wait for final result
                final_received = False
                while not final_received:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=10)
                        data = json.loads(msg)
                        
                        if data.get('type') == 'final_result':
                            self.metrics['final_result_time'] = time.time() - start_total
                            self.metrics['total_time'] = self.metrics['final_result_time']
                            
                            print_success(f"Final result received")
                            print_data("Detected Text", data.get('detected_text', 'N/A')[:50])
                            print_data("Intent", data.get('intent', 'UNKNOWN'))
                            print_data("Confidence", f"{data.get('confidence', 0):.2%}")
                            print_data("Response", data.get('response', 'N/A')[:50])
                            print_data("Processing Time", f"{data.get('processing_time_ms', 0)}ms")
                            print_data("Total Round Trip", f"{self.metrics['final_result_time']*1000:.1f}ms")
                            
                            self.test_results['passed'].append("Final Processing")
                            final_received = True
                    except asyncio.TimeoutError:
                        print_error("Timeout waiting for final result")
                        self.test_results['failed'].append("Final Processing: Timeout")
                        return False
                
                return True
        except Exception as e:
            print_error(f"Final processing test failed: {str(e)}")
            self.test_results['failed'].append(f"Final Processing: {str(e)}")
            return False
    
    async def test_error_handling(self):
        """Test 6: Error Handling"""
        print_header("Test 6: Error Handling")
        try:
            async with websockets.connect(self.ws_url) as ws:
                # Initialize
                await ws.recv()  # connection
                await ws.send(json.dumps({
                    'type': 'init',
                    'language': TEST_CONFIG['language'],
                    'include_tts': False
                }))
                await ws.recv()  # session_ready
                
                # Send invalid message type
                await ws.send(json.dumps({
                    'type': 'invalid_type'
                }))
                
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(msg)
                    
                    if data.get('type') == 'error':
                        print_success(f"Error handling working")
                        print_data("Error Message", data.get('message', 'N/A'))
                        self.test_results['passed'].append("Error Handling")
                        return True
                except asyncio.TimeoutError:
                    print_error("No error response received")
                    self.test_results['failed'].append("Error Handling")
                    return False
        except Exception as e:
            print_error(f"Error handling test failed: {str(e)}")
            self.test_results['failed'].append(f"Error Handling: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        print_header("Voice Bot WebSocket Streaming Test Suite")
        print_info(f"WebSocket URL: {self.ws_url}")
        print_info(f"Language: {TEST_CONFIG['language']}")
        print_info(f"Timestamp: {datetime.now().isoformat()}")
        
        tests = [
            ("Connection Test", self.test_connection),
            ("Session Initialization", self.test_session_init),
            ("Audio Chunk Reception", self.test_audio_chunk_reception),
            ("Partial Updates", self.test_partial_updates),
            ("Final Processing", self.test_final_processing),
            ("Error Handling", self.test_error_handling),
        ]
        
        for test_name, test_func in tests:
            try:
                await test_func()
            except Exception as e:
                print_error(f"Unexpected error in {test_name}: {str(e)}")
                self.test_results['failed'].append(f"{test_name}: {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print_header("Test Results Summary")
        
        total = len(self.test_results['passed']) + len(self.test_results['failed'])
        
        print_success(f"{len(self.test_results['passed'])} tests passed")
        for test in self.test_results['passed']:
            print(f"  ✓ {test}")
        
        if self.test_results['failed']:
            print_error(f"{len(self.test_results['failed'])} tests failed")
            for test in self.test_results['failed']:
                print(f"  ✗ {test}")
        
        if self.test_results['warnings']:
            print_info(f"{len(self.test_results['warnings'])} warnings")
            for test in self.test_results['warnings']:
                print(f"  ⚠ {test}")
        
        print_header("Performance Metrics")
        print_data("Connection Time", f"{self.metrics['connection_time']*1000:.1f}ms")
        print_data("Session Init Time", f"{self.metrics['session_init_time']*1000:.1f}ms")
        print_data("First Chunk RTT", f"{self.metrics['first_chunk_time']*1000:.1f}ms")
        print_data("Final Result Time", f"{self.metrics['final_result_time']*1000:.1f}ms")
        print_data("Total Time", f"{self.metrics['total_time']*1000:.1f}ms")
        
        # Exit code
        if self.test_results['failed']:
            print_error("\n❌ Some tests failed")
            sys.exit(1)
        else:
            print_success("\n✅ All tests passed!")
            sys.exit(0)

async def main():
    parser = argparse.ArgumentParser(description='Voice Bot WebSocket Streaming Test')
    parser.add_argument('--url', default='ws://localhost:8000/ws/voice-stream/', 
                        help='WebSocket URL to test')
    parser.add_argument('--audio', help='Audio file to test with')
    
    args = parser.parse_args()
    
    test = VoiceBotStreamingTest(args.url, args.audio)
    await test.run_all_tests()

if __name__ == '__main__':
    asyncio.run(main())
