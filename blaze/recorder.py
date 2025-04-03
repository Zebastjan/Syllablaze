import os
import sys
import io
import logging
import warnings
import ctypes
import numpy as np
import pyaudio
from PyQt6.QtCore import QObject, pyqtSignal
from blaze.settings import Settings
from blaze.constants import (
    WHISPER_SAMPLE_RATE, SAMPLE_RATE_MODE_WHISPER,
    DEFAULT_SAMPLE_RATE_MODE
)
from blaze.audio_processor import AudioProcessor  # Import our new unified audio processor

# Set environment variables to suppress Jack errors
os.environ['JACK_NO_AUDIO_RESERVATION'] = '1'
os.environ['JACK_NO_START_SERVER'] = '1'
os.environ['DISABLE_JACK'] = '1'

# Create a custom stderr filter
class JackErrorFilter:
    def __init__(self, real_stderr):
        self.real_stderr = real_stderr
        self.buffer = ""
        
    def write(self, text):
        # Filter out Jack-related error messages
        if any(msg in text for msg in [
            "jack server",
            "Cannot connect to server",
            "JackShmReadWritePtr"
        ]):
            return
        self.real_stderr.write(text)
        
    def flush(self):
        self.real_stderr.flush()

# Replace stderr with our filtered version
sys.stderr = JackErrorFilter(sys.stderr)

logger = logging.getLogger(__name__)

class AudioRecorder(QObject):
    # Use past tense for events that have occurred
    recording_completed = pyqtSignal(object)  # Emits audio data as numpy array
    recording_failed = pyqtSignal(str)
    # Use present continuous for ongoing updates
    volume_changing = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        
        # Create a custom error handler for audio system errors
        ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int,
                                            ctypes.c_char_p, ctypes.c_int,
                                            ctypes.c_char_p)
        
        def py_error_handler(filename, line, function, err, fmt):
            # Completely ignore all audio system errors
            pass
        
        c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
        
        # Redirect stderr to capture Jack errors
        original_stderr = sys.stderr
        sys.stderr = io.StringIO()
        
        try:
            # Try to load and configure ALSA error handler
            try:
                asound = ctypes.cdll.LoadLibrary('libasound.so.2')
                asound.snd_lib_error_set_handler(c_error_handler)
                logger.info("ALSA error handler configured")
            except Exception:
                logger.info("ALSA error handler not available - continuing anyway")
            
            # Initialize PyAudio with all warnings suppressed
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.audio = pyaudio.PyAudio()
                
            logger.info("Audio system initialized successfully")
            
        finally:
            # Restore stderr and check if Jack errors were reported
            jack_errors = sys.stderr.getvalue()
            sys.stderr = original_stderr
            
            if "jack server is not running" in jack_errors:
                logger.info("Jack server not available - using alternative audio backend")
        
        self.stream = None
        self.frames = []
        self.is_recording_active = False
        self.is_microphone_test_running = False
        self.test_stream = None
        self.current_device_info = None
        # Keep a reference to self to prevent premature deletion
        self._instance = self
        
    def update_sample_rate_mode(self, mode):
        """Update the sample rate mode setting"""
        settings = Settings()
        settings.set('sample_rate_mode', mode)
        logger.info(f"Sample rate mode updated to: {mode}")
        
    def start_recording(self):
        if self.is_recording_active:
            return
            
        try:
            self.frames = []
            self.is_recording_active = True
            
            # Get settings
            settings = Settings()
            mic_index = settings.get('mic_index')
            sample_rate_mode = settings.get('sample_rate_mode', DEFAULT_SAMPLE_RATE_MODE)
            
            try:
                mic_index = int(mic_index) if mic_index is not None else None
            except (ValueError, TypeError):
                mic_index = None
            
            # Get device info
            if mic_index is not None:
                device_info = self.audio.get_device_info_by_index(mic_index)
                logger.info(f"Using selected input device: {device_info['name']}")
            else:
                device_info = self.audio.get_default_input_device_info()
                logger.info(f"Using default input device: {device_info['name']}")
                mic_index = device_info['index']
            
            # Store device info for later use
            self.current_device_info = device_info
            
            # Determine sample rate based on mode
            if sample_rate_mode == SAMPLE_RATE_MODE_WHISPER:
                # Try to use 16kHz (Whisper-optimized)
                target_sample_rate = WHISPER_SAMPLE_RATE
                logger.info(f"Using Whisper-optimized sample rate: {target_sample_rate}Hz")
                
                try:
                    self.stream = self.audio.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=target_sample_rate,
                        input=True,
                        input_device_index=mic_index,
                        frames_per_buffer=1024,
                        stream_callback=self._handle_audio_frame
                    )
                    # If successful, store the sample rate
                    self.current_sample_rate = target_sample_rate
                    logger.info(f"Successfully recording at {target_sample_rate}Hz")
                    
                except Exception as e:
                    # If 16kHz fails, fall back to device default
                    logger.warning(f"Failed to record at {target_sample_rate}Hz: {e}")
                    logger.info("Falling back to device's default sample rate")
                    
                    default_sample_rate = int(device_info['defaultSampleRate'])
                    logger.info(f"Using fallback sample rate: {default_sample_rate}Hz")
                    
                    self.stream = self.audio.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=default_sample_rate,
                        input=True,
                        input_device_index=mic_index,
                        frames_per_buffer=1024,
                        stream_callback=self._handle_audio_frame
                    )
                    # Store the sample rate
                    self.current_sample_rate = default_sample_rate
                    
            else:  # SAMPLE_RATE_MODE_DEVICE
                # Use device's default sample rate
                default_sample_rate = int(device_info['defaultSampleRate'])
                logger.info(f"Using device's default sample rate: {default_sample_rate}Hz")
                
                self.stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=default_sample_rate,
                    input=True,
                    input_device_index=mic_index,
                    frames_per_buffer=1024,
                    stream_callback=self._handle_audio_frame
                )
                # Store the sample rate
                self.current_sample_rate = default_sample_rate
            
            self.stream.start_stream()
            logger.info(f"Recording started at {self.current_sample_rate}Hz")
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.recording_failed.emit(f"Failed to start recording: {e}")
            self.is_recording_active = False
        
    def _handle_audio_frame(self, in_data, frame_count, time_info, status):
        if status:
            logger.warning(f"Recording status: {status}")
        try:
            if self.is_recording_active:
                self.frames.append(in_data)
                # Calculate and emit volume level using our unified AudioProcessor
                try:
                    audio_data = np.frombuffer(in_data, dtype=np.int16)
                    volume = AudioProcessor.calculate_volume(audio_data)
                    self.volume_changing.emit(volume)
                except Exception as e:
                    logger.error(f"Error calculating volume: {e}")
                    self.volume_changing.emit(0.0)
                return (in_data, pyaudio.paContinue)
        except RuntimeError:
            # Handle case where object is being deleted
            logger.warning("AudioRecorder object is being cleaned up")
            return (in_data, pyaudio.paComplete)
        return (in_data, pyaudio.paComplete)
        
    def _stop_recording(self):
        """Internal method to safely stop audio recording and process captured data"""
        if not self.is_recording_active:
            return
            
        logger.info("Stopping audio recording")
        self.is_recording_active = False
        
        try:
            # Stop and close the stream first
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # Check if we have any recorded frames
            if not self.frames:
                logger.error("No audio data recorded")
                self.recording_failed.emit("No audio was recorded")
                return
            
            # Process the recording
            self._process_recorded_audio()
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self.recording_failed.emit(f"Error stopping recording: {e}")

    def _process_recorded_audio(self):
        """Process the recorded audio data for transcription"""
        try:
            logger.info("Processing recording in memory...")
            
            # Verify we have frames to process
            if not self.frames:
                raise ValueError("No audio frames available for processing")
            
            # Use our unified AudioProcessor to process the audio
            if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
                logger.warning("No sample rate information available, assuming device default")
                original_rate = AudioProcessor.get_device_sample_rate(self.audio, self.current_device_info)
            else:
                original_rate = self.current_sample_rate
            
            # Process the audio frames for transcription
            audio_data = AudioProcessor.process_audio_for_transcription(
                self.frames, original_rate
            )
            
            # Verify audio data was generated
            if audio_data is None or len(audio_data) == 0:
                raise ValueError("Processed audio data is empty")
            
            logger.info(f"Recording processed in memory (length: {len(audio_data)} samples)")
            self.recording_completed.emit(audio_data)
        except Exception as e:
            logger.error(f"Failed to process recording: {str(e)}", exc_info=True)
            self.recording_failed.emit(f"Failed to process recording: {str(e)}")
        
    def save_audio(self, filename):
        """Save recorded audio to a WAV file"""
        try:
            # Convert frames to numpy array using our unified AudioProcessor
            audio_data_int16 = AudioProcessor.frames_to_numpy(self.frames)
            
            # Get the original sample rate
            if not hasattr(self, 'current_sample_rate') or self.current_sample_rate is None:
                original_rate = AudioProcessor.get_device_sample_rate(self.audio, self.current_device_info)
            else:
                original_rate = self.current_sample_rate
            
            # Resample to Whisper rate if needed
            if original_rate != WHISPER_SAMPLE_RATE:
                audio_data_int16 = AudioProcessor.resample_audio(
                    audio_data_int16, original_rate, WHISPER_SAMPLE_RATE
                )
            
            # Save to WAV file using our unified AudioProcessor
            AudioProcessor.save_to_wav(
                audio_data_int16,
                filename,
                WHISPER_SAMPLE_RATE,  # Always save at 16000Hz for Whisper
                channels=1,
                sample_width=self.audio.get_sample_size(pyaudio.paInt16)
            )
            
            # Log the saved file location
            logger.info(f"Recording saved to: {os.path.abspath(filename)}")
            
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")
            raise
        
    def start_microphone_test(self, microphone_device_index):
        """Start a test recording from the specified microphone device"""
        if self.is_microphone_test_running or self.is_recording_active:
            return
            
        try:
            self.test_stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=44100,
                input=True,
                input_device_index=microphone_device_index,
                frames_per_buffer=1024,
                stream_callback=self._test_callback
            )
            
            self.test_stream.start_stream()
            self.is_microphone_test_running = True
            logger.info(f"Started mic test on device {microphone_device_index}")
            
        except Exception as e:
            logger.error(f"Failed to start mic test: {e}")
            raise
            
    def stop_microphone_test(self):
        """Stop the microphone test recording"""
        if self.test_stream:
            self.test_stream.stop_stream()
            self.test_stream.close()
            self.test_stream = None
        self.is_microphone_test_running = False
        
    def _test_callback(self, in_data, frame_count, time_info, status):
        """Handle audio frames during microphone testing"""
        if status:
            logger.warning(f"Test callback status: {status}")
        return (in_data, pyaudio.paContinue)
        
    def get_current_audio_level(self):
        """Get current audio level for the microphone test meter"""
        if not self.test_stream or not self.is_microphone_test_running:
            return 0
            
        try:
            data = self.test_stream.read(1024, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.float32)
            # Use our unified AudioProcessor to calculate volume
            return AudioProcessor.calculate_volume(audio_data)
        except Exception as e:
            logger.error(f"Error getting audio level: {e}")
            return 0

    def cleanup(self):
        """Cleanup resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.test_stream:
            self.test_stream.stop_stream()
            self.test_stream.close()
            self.test_stream = None
        if self.audio:
            self.audio.terminate()
            self.audio = None
        self._instance = None
