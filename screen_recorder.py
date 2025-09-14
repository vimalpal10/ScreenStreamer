import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import numpy as np
import pyaudio
import wave
import threading
import time
import os
from datetime import datetime

# Import moviepy for audio-video muxing
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# Handle display-related imports for headless environments
try:
    import pyautogui
    # Disable failsafe for automated environments
    pyautogui.FAILSAFE = False
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False
except Exception:
    # Handle X11 display issues in headless environments
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False

# Mock pyautogui functions for headless environments
class MockPyAutoGUI:
    @staticmethod
    def size():
        return (1920, 1080)  # Default screen size
    
    @staticmethod
    def screenshot():
        # Create a mock screenshot (black image)
        import numpy as np
        from PIL import Image
        return Image.fromarray(np.zeros((1080, 1920, 3), dtype=np.uint8))

if not PYAUTOGUI_AVAILABLE:
    pyautogui = MockPyAutoGUI()


class ScreenRecorder:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows 10 Screen Recorder")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Recording state variables
        self.is_recording = False
        self.is_paused = False
        self.video_writer = None
        self.audio_thread = None
        self.video_thread = None
        self.output_filename = None
        self.temp_audio_file = None
        
        # Audio recording variables
        self.audio_frames = []
        self.audio_stream = None
        self.audio_format = pyaudio.paInt16
        self.audio_channels = 2
        self.audio_rate = 44100
        self.audio_chunk = 1024
        
        # Resolution options
        self.resolution_options = {
            "HD (720p)": (1280, 720),
            "Full HD (1080p)": (1920, 1080),
            "4K (2160p)": (3840, 2160)
        }
        
        # Audio input options
        self.audio_options = {
            "No Audio": "none",
            "System Microphone": "system_mic",
            "External Headphone Mic": "external_mic"
        }
        
        self.setup_ui()
        
        # Check if we're in a supported environment
        if not PYAUTOGUI_AVAILABLE:
            self.show_environment_warning()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        
        # Title
        title_label = ttk.Label(main_frame, text="Screen Recorder", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Resolution selection
        ttk.Label(main_frame, text="Recording Quality:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.resolution_var = tk.StringVar(value="Full HD (1080p)")
        resolution_combo = ttk.Combobox(main_frame, textvariable=self.resolution_var, 
                                      values=list(self.resolution_options.keys()), 
                                      state="readonly", width=25)
        resolution_combo.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # Audio selection
        ttk.Label(main_frame, text="Audio Input:").grid(row=2, column=0, sticky=tk.W, pady=(0, 20))
        self.audio_var = tk.StringVar(value="System Microphone")
        audio_combo = ttk.Combobox(main_frame, textvariable=self.audio_var,
                                 values=list(self.audio_options.keys()),
                                 state="readonly", width=25)
        audio_combo.grid(row=2, column=1, sticky=tk.W, pady=(0, 20))
        
        # Control buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0))
        
        # Recording control buttons
        self.start_button = ttk.Button(button_frame, text="Start Recording", 
                                     command=self.start_recording, width=15)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.pause_button = ttk.Button(button_frame, text="Pause", 
                                     command=self.pause_recording, width=15, state="disabled")
        self.pause_button.grid(row=0, column=1, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop Recording", 
                                    command=self.stop_recording, width=15, state="disabled")
        self.stop_button.grid(row=1, column=0, pady=(10, 0), padx=(0, 10))
        
        self.resume_button = ttk.Button(button_frame, text="Resume", 
                                      command=self.resume_recording, width=15, state="disabled")
        self.resume_button.grid(row=1, column=1, pady=(10, 0))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to record", foreground="green")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=(30, 0))
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0), sticky=tk.W+tk.E)
        
        # Recording time label
        self.time_label = ttk.Label(progress_frame, text="Recording Time: 00:00:00")
        self.time_label.grid(row=0, column=0, sticky=tk.W)
        
        # Output location display
        self.output_label = ttk.Label(main_frame, text="", wraplength=450, foreground="blue")
        self.output_label.grid(row=6, column=0, columnspan=2, pady=(20, 0))
    
    def show_environment_warning(self):
        """Show warning for non-Windows environments"""
        warning_msg = ("⚠️ Environment Notice\n\n"
                      "This application is designed for Windows 10 with full desktop access. "
                      "In this environment, screen recording functionality is simulated for "
                      "development and testing purposes.\n\n"
                      "For full functionality, please run this application on a Windows 10 "
                      "machine with Python and the required dependencies installed.")
        messagebox.showwarning("Environment Notice", warning_msg)
        
    def get_screen_size(self):
        """Get current screen size"""
        return pyautogui.size()
    
    def calculate_recording_resolution(self, target_resolution):
        """Calculate actual recording resolution based on screen size and target"""
        screen_width, screen_height = self.get_screen_size()
        target_width, target_height = target_resolution
        
        # Scale down if screen is smaller than target resolution
        if screen_width < target_width or screen_height < target_height:
            scale = min(screen_width / target_width, screen_height / target_height)
            actual_width = int(target_width * scale)
            actual_height = int(target_height * scale)
            # Ensure even dimensions for video encoding
            actual_width = actual_width if actual_width % 2 == 0 else actual_width - 1
            actual_height = actual_height if actual_height % 2 == 0 else actual_height - 1
            return (actual_width, actual_height)
        else:
            return target_resolution
    
    def setup_audio_recording(self):
        """Setup audio recording based on selected option"""
        audio_option = self.audio_options[self.audio_var.get()]
        
        if audio_option == "none":
            return False
            
        try:
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            
            # Find appropriate audio device
            device_index = None
            if audio_option == "system_mic":
                # Use default input device
                device_index = None
            elif audio_option == "external_mic":
                # Try to find external microphone (this is a simplified approach)
                for i in range(self.audio.get_device_count()):
                    device_info = self.audio.get_device_info_by_index(i)
                    device_name = str(device_info.get('name', ''))
                    max_input_channels = device_info.get('maxInputChannels', 0)
                    if isinstance(max_input_channels, (int, float)) and max_input_channels > 0 and 'headset' in device_name.lower():
                        device_index = i
                        break
                # If no specific external mic found, use default
                if device_index is None:
                    device_index = None
            
            # Create audio stream
            self.audio_stream = self.audio.open(
                format=self.audio_format,
                channels=self.audio_channels,
                rate=self.audio_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.audio_chunk
            )
            
            return True
            
        except Exception as e:
            print(f"Audio setup error: {e}")
            return False
    
    def record_audio(self):
        """Record audio in a separate thread"""
        self.audio_frames = []
        
        try:
            while self.is_recording:
                if not self.is_paused and self.audio_stream:
                    data = self.audio_stream.read(self.audio_chunk, exception_on_overflow=False)
                    self.audio_frames.append(data)
                else:
                    time.sleep(0.1)  # Sleep when paused
        except Exception as e:
            print(f"Audio recording error: {e}")
    
    def save_audio(self):
        """Save recorded audio to temporary file"""
        if not self.audio_frames:
            return None
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_audio_file = f"temp_audio_{timestamp}.wav"
            
            with wave.open(temp_audio_file, 'wb') as wf:
                wf.setnchannels(self.audio_channels)
                wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                wf.setframerate(self.audio_rate)
                wf.writeframes(b''.join(self.audio_frames))
                
            return temp_audio_file
            
        except Exception as e:
            print(f"Audio save error: {e}")
            return None
    
    def merge_audio_video(self, video_file, audio_file):
        """Merge audio and video files using moviepy"""
        try:
            # Load video and audio clips
            video_clip = VideoFileClip(video_file)
            audio_clip = AudioFileClip(audio_file)
            
            # Get minimum duration to avoid sync issues
            min_duration = min(video_clip.duration, audio_clip.duration)
            
            # Trim clips to same duration
            video_clip = video_clip.subclip(0, min_duration)
            audio_clip = audio_clip.subclip(0, min_duration)
            
            # Set audio to video
            final_clip = video_clip.set_audio(audio_clip)
            
            # Create output filename for final video
            base_name = os.path.splitext(video_file)[0]
            final_output = f"{base_name}_with_audio.mp4"
            
            # Write final video with audio
            final_clip.write_videofile(final_output, codec='libx264', audio_codec='aac', verbose=False, logger=None)
            
            # Close clips to free memory
            video_clip.close()
            audio_clip.close()
            final_clip.close()
            
            # Replace original video file with merged version
            try:
                os.remove(video_file)
                os.rename(final_output, video_file)
            except:
                # If renaming fails, keep both files
                self.output_filename = final_output
            
            return True
            
        except Exception as e:
            print(f"Audio-video merge error: {e}")
            return False
    
    def record_video(self):
        """Record video in a separate thread"""
        start_time = time.time()
        
        try:
            while self.is_recording:
                if not self.is_paused:
                    # Capture screenshot
                    screenshot = pyautogui.screenshot()
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Resize frame to target resolution if needed
                    target_resolution = self.resolution_options[self.resolution_var.get()]
                    actual_resolution = self.calculate_recording_resolution(target_resolution)
                    
                    if frame.shape[:2][::-1] != actual_resolution:
                        frame = cv2.resize(frame, actual_resolution)
                    
                    # Write frame to video
                    if self.video_writer:
                        self.video_writer.write(frame)
                    
                    # Update recording time
                    elapsed_time = int(time.time() - start_time)
                    time_str = f"{elapsed_time // 3600:02d}:{(elapsed_time % 3600) // 60:02d}:{elapsed_time % 60:02d}"
                    self.root.after(0, lambda: self.time_label.config(text=f"Recording Time: {time_str}"))
                    
                    # Control frame rate (approximately 30 FPS)
                    time.sleep(1/30)
                else:
                    time.sleep(0.1)  # Sleep when paused
                    
        except Exception as e:
            print(f"Video recording error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Video recording failed: {e}"))
    
    def start_recording(self):
        """Start the recording process"""
        try:
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_filename = f"screen_recording_{timestamp}.mp4"
            
            # Get recording resolution
            target_resolution = self.resolution_options[self.resolution_var.get()]
            actual_resolution = self.calculate_recording_resolution(target_resolution)
            
            # Setup video writer
            fourcc = cv2.VideoWriter.fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(self.output_filename, fourcc, 30.0, actual_resolution)
            
            if not self.video_writer.isOpened():
                raise Exception("Failed to initialize video writer")
            
            # Setup audio recording if selected
            audio_enabled = self.setup_audio_recording()
            
            # Update UI state
            self.is_recording = True
            self.is_paused = False
            self.start_button.config(state="disabled")
            self.pause_button.config(state="normal")
            self.stop_button.config(state="normal")
            
            # Show recording status with audio info
            audio_status = " (with audio)" if audio_enabled else " (video only)"
            self.status_label.config(text=f"Recording...{audio_status}", foreground="red")
            
            # Start recording threads
            self.video_thread = threading.Thread(target=self.record_video, daemon=True)
            self.video_thread.start()
            
            if audio_enabled:
                self.audio_thread = threading.Thread(target=self.record_audio, daemon=True)
                self.audio_thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start recording: {e}")
            self.reset_ui_state()
    
    def pause_recording(self):
        """Pause the recording"""
        self.is_paused = True
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="normal")
        self.status_label.config(text="Recording Paused", foreground="orange")
    
    def resume_recording(self):
        """Resume the recording"""
        self.is_paused = False
        self.pause_button.config(state="normal")
        self.resume_button.config(state="disabled")
        self.status_label.config(text="Recording...", foreground="red")
    
    def stop_recording(self):
        """Stop the recording and save the file"""
        try:
            # Stop recording
            self.is_recording = False
            
            # Wait for threads to finish
            if self.video_thread and self.video_thread.is_alive():
                self.video_thread.join(timeout=5)
            
            if self.audio_thread and self.audio_thread.is_alive():
                self.audio_thread.join(timeout=5)
            
            # Release video writer
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            # Clean up audio
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
            
            if hasattr(self, 'audio'):
                self.audio.terminate()
            
            # Save and merge audio if recorded
            if self.audio_frames and MOVIEPY_AVAILABLE:
                self.status_label.config(text="Processing audio...", foreground="orange")
                self.root.update()
                
                temp_audio_file = self.save_audio()
                if temp_audio_file:
                    self.temp_audio_file = temp_audio_file
                    # Merge audio and video using moviepy
                    success = self.merge_audio_video(self.output_filename, temp_audio_file)
                    if not success:
                        messagebox.showwarning("Audio Warning", 
                                             f"Video saved successfully but audio merge failed.\n"
                                             f"Video: {self.output_filename}\n"
                                             f"Audio: {temp_audio_file}")
                    else:
                        # Clean up temporary audio file
                        try:
                            os.remove(temp_audio_file)
                        except:
                            pass
            elif self.audio_frames and not MOVIEPY_AVAILABLE:
                # Save audio separately if moviepy not available
                temp_audio_file = self.save_audio()
                if temp_audio_file:
                    messagebox.showinfo("Audio Saved Separately", 
                                      f"Video: {self.output_filename}\n"
                                      f"Audio: {temp_audio_file}\n\n"
                                      f"Install moviepy to automatically merge audio/video.")
            
            # Reset UI state
            self.reset_ui_state()
            
            # Show completion message
            full_path = os.path.abspath(self.output_filename) if self.output_filename else ''
            self.output_label.config(text=f"Recording saved to: {full_path}")
            messagebox.showinfo("Recording Complete", 
                              f"Recording saved successfully!\n\nLocation: {full_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop recording: {e}")
            self.reset_ui_state()
    
    def reset_ui_state(self):
        """Reset UI to initial state"""
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.status_label.config(text="Ready to record", foreground="green")
        self.time_label.config(text="Recording Time: 00:00:00")
    
    def on_closing(self):
        """Handle application closing"""
        if self.is_recording:
            if messagebox.askokcancel("Quit", "Recording is in progress. Stop recording and quit?"):
                self.stop_recording()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = ScreenRecorder(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()


if __name__ == "__main__":
    main()