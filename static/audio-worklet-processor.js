/**
 * AudioWorkletProcessor for Real-Time Audio Capture
 * 
 * This runs in a separate thread (Web Worker) and captures audio data
 * from the microphone stream in real-time without blocking the main thread.
 * 
 * Replaces deprecated ScriptProcessorNode for better performance
 */

class AudioCaptureProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
        
        // Configuration
        this.targetSampleRate = 16000;
        this.inputSampleRate = 44100; // Will be set by init message
        this.resampleBuffer = [];
        this.maxBufferSize = 100000; // Prevent infinite growth (~2.3 seconds at 16kHz)
        
        // VAD (Voice Activity Detection)
        this.vadThreshold = 0.01; // RMS threshold for silence detection
        this.frameCount = 0;
        this.silenceFrameCount = 0;
        
        // Listen for init message with actual sample rate
        this.port.onmessage = (event) => {
            const { type, sampleRate } = event.data;
            if (type === 'INIT') {
                this.inputSampleRate = sampleRate;
                console.log(`[AudioWorklet] Initialized - Input SR: ${sampleRate}Hz, Target: ${this.targetSampleRate}Hz`);
            }
        };
    }
    
    /**
     * CRITICAL: Process audio from microphone
     * Called by Web Audio API for each buffer (~2048 samples)
     */
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (!input || !input[0]) return true;
        
        const channelData = input[0]; // Get mono channel
        
        // Calculate RMS for VAD
        const rms = this._calculateRMS(channelData);
        const isVoiceDetected = rms >= this.vadThreshold;
        
        // Add to resample buffer
        for (let i = 0; i < channelData.length; i++) {
            this.resampleBuffer.push(channelData[i]);
        }
        
        this.frameCount++;
        if (!isVoiceDetected) {
            this.silenceFrameCount++;
        }
        
        // Send data every ~128ms (at 16kHz = ~2048 samples)
        // This provides real-time streaming without flooding the network
        const targetChunkSize = Math.floor(this.targetSampleRate * 0.128); // ~2048 @ 16kHz
        
        if (this.resampleBuffer.length >= targetChunkSize) {
            // Extract chunk
            const chunk = this.resampleBuffer.splice(0, targetChunkSize);
            
            // Downsample from input rate to 16kHz
            const downsampled = this._downsample(chunk, this.inputSampleRate, this.targetSampleRate);
            
            // Convert Float32 to Int16 PCM
            const int16Data = this._float32ToInt16(downsampled);
            
            // Send to main thread
            this.port.postMessage({
                type: 'AUDIO_CHUNK',
                data: int16Data,
                rms: rms,
                isVoice: isVoiceDetected,
                silenceRatio: this.silenceFrameCount / this.frameCount
            });
            
            // Reset counters
            this.frameCount = 0;
            this.silenceFrameCount = 0;
        }
        
        // Prevent infinite buffer growth
        if (this.resampleBuffer.length > this.maxBufferSize) {
            console.warn('[AudioWorklet] Buffer overflow, trimming old data');
            this.resampleBuffer = this.resampleBuffer.slice(-this.maxBufferSize);
        }
        
        return true; // Keep processor alive
    }
    
    /**
     * Proper downsampling from inputRate to outputRate
     * Uses linear interpolation for smooth resampling
     */
    _downsample(buffer, inputRate, outputRate) {
        if (inputRate === outputRate) {
            return buffer;
        }
        
        const ratio = inputRate / outputRate;
        const outputLength = Math.ceil(buffer.length / ratio);
        const resampled = new Float32Array(outputLength);
        
        // Linear interpolation resampling
        let j = 0;
        for (let i = 0; i < outputLength; i++) {
            const pos = i * ratio;
            const index = Math.floor(pos);
            const fraction = pos - index;
            
            // Linear interpolation between samples
            const sample1 = buffer[Math.min(index, buffer.length - 1)];
            const sample2 = buffer[Math.min(index + 1, buffer.length - 1)];
            
            resampled[i] = sample1 + (sample2 - sample1) * fraction;
        }
        
        return resampled;
    }
    
    /**
     * Convert Float32 audio (-1.0 to 1.0) to Int16 PCM (signed 16-bit)
     */
    _float32ToInt16(float32Data) {
        const int16Data = new Int16Array(float32Data.length);
        
        for (let i = 0; i < float32Data.length; i++) {
            // Clamp to valid range
            let s = Math.max(-1, Math.min(1, float32Data[i]));
            
            // Convert to 16-bit signed integer
            int16Data[i] = s < 0 
                ? s * 0x8000      // Negative: multiply by 32768
                : s * 0x7FFF;     // Positive: multiply by 32767
        }
        
        return int16Data;
    }
    
    /**
     * Calculate RMS (Root Mean Square) for voice detection
     * RMS > threshold = voice, RMS < threshold = silence
     */
    _calculateRMS(buffer) {
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
            sum += buffer[i] * buffer[i];
        }
        return Math.sqrt(sum / buffer.length);
    }
}

// Register this processor
registerProcessor('audio-capture-processor', AudioCaptureProcessor);
