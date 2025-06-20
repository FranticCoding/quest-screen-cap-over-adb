#!/usr/bin/env python3
"""
Oculus Quest ADB Screen Capture Tool
Connects to Oculus Quest via ADB to capture screenshots or stream video
"""

import subprocess
import time
import os
import sys
from datetime import datetime
import threading
import socket
try:
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image, ImageTk
    import io
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("Note: PIL (Pillow) and tkinter not available. Real-time viewer will be disabled.")

class QuestADBCapture:
    def __init__(self, device_ip=None, adb_port=5555):
        self.device_ip = device_ip
        self.adb_port = adb_port
        self.connected = False
        self.streaming = False
        self.output_folder = self.setup_output_folder()
        
    def setup_output_folder(self):
        """Setup the output folder for screenshots and recordings"""
        import platform
        
        # Determine the base path based on operating system
        system = platform.system().lower()
        
        if system == "windows":
            # Try C:\Program Files first, fallback to user directory if no permissions
            try:
                base_path = r"C:\Program Files\Quest Screen Capture"
                # Test write permissions
                os.makedirs(base_path, exist_ok=True)
                test_file = os.path.join(base_path, "test_write.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                print(f"Output folder: {base_path}")
                return base_path
            except (PermissionError, OSError):
                # Fallback to user Documents folder
                import os
                fallback_path = os.path.join(os.path.expanduser("~"), "Documents", "Quest Screen Capture")
                os.makedirs(fallback_path, exist_ok=True)
                print(f"No permission for Program Files. Using: {fallback_path}")
                return fallback_path
        
        elif system == "darwin":  # macOS
            base_path = os.path.join(os.path.expanduser("~"), "Quest Screen Capture")
            os.makedirs(base_path, exist_ok=True)
            print(f"Output folder: {base_path}")
            return base_path
            
        else:  # Linux and others
            base_path = os.path.join(os.path.expanduser("~"), "Quest Screen Capture")
            os.makedirs(base_path, exist_ok=True)
            print(f"Output folder: {base_path}")
            return base_path
        
    def check_adb_installed(self):
        """Check if ADB is installed and accessible"""
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("ADB is installed and accessible")
                return True
            else:
                print("ADB not found. Please install Android SDK Platform Tools")
                return False
        except FileNotFoundError:
            print("ADB not found. Please install Android SDK Platform Tools")
            return False
    
    def connect_device(self):
        """Connect to Oculus Quest device via ADB"""
        if not self.check_adb_installed():
            return False
            
        try:
            if self.device_ip:
                # Connect via WiFi
                print(f"Connecting to {self.device_ip}:{self.adb_port}")
                result = subprocess.run(['adb', 'connect', f'{self.device_ip}:{self.adb_port}'], 
                                      capture_output=True, text=True)
                if "connected" in result.stdout.lower():
                    print("Successfully connected via WiFi")
                    self.connected = True
                else:
                    print(f"Failed to connect: {result.stdout}")
                    return False
            else:
                # Check for USB connected devices with retry logic
                max_attempts = 3
                for attempt in range(max_attempts):
                    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    devices = [line.split('\t')[0] for line in lines if '\tdevice' in line]
                    
                    if devices:
                        print(f"Found {len(devices)} device(s): {', '.join(devices)}")
                        self.connected = True
                        break
                    else:
                        if attempt < max_attempts - 1:
                            print(f"No devices found (attempt {attempt + 1}/{max_attempts}). Waiting 5 seconds...")
                            print("Make sure your Quest is connected and developer mode is enabled")
                            time.sleep(5)
                        else:
                            print("No devices found after multiple attempts. Please check connection and try again.")
                            return False
            
            return True
            
        except Exception as e:
            print(f"Error connecting to device: {e}")
            return False
    
    def get_device_info(self):
        """Get basic device information"""
        if not self.connected:
            print("Device not connected")
            return None
            
        try:
            # Get device model
            model_result = subprocess.run(['adb', 'shell', 'getprop', 'ro.product.model'], 
                                        capture_output=True, text=True)
            model = model_result.stdout.strip()
            
            # Get Android version
            version_result = subprocess.run(['adb', 'shell', 'getprop', 'ro.build.version.release'], 
                                          capture_output=True, text=True)
            android_version = version_result.stdout.strip()
            
            # Get screen resolution
            res_result = subprocess.run(['adb', 'shell', 'wm', 'size'], 
                                      capture_output=True, text=True)
            resolution = res_result.stdout.strip()
            
            info = {
                'model': model,
                'android_version': android_version,
                'resolution': resolution
            }
            
            print(f"Device Info:")
            print(f"  Model: {model}")
            print(f"  Android Version: {android_version}")
            print(f"  {resolution}")
            
            return info
            
        except Exception as e:
            print(f"Error getting device info: {e}")
            return None
    
    def take_screenshot(self, filename=None):
        """Take a screenshot from the Quest headset"""
        if not self.connected:
            print("Device not connected")
            return False
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quest_screenshot_{timestamp}.png"
        
        # Ensure filename has .png extension
        if not filename.lower().endswith('.png'):
            filename += '.png'
            
        # Full path to output folder
        full_path = os.path.join(self.output_folder, filename)
        
        try:
            # Take screenshot on device
            print("Taking screenshot...")
            subprocess.run(['adb', 'shell', 'screencap', '-p', '/sdcard/screenshot.png'], 
                          check=True)
            
            # Pull screenshot to local machine
            subprocess.run(['adb', 'pull', '/sdcard/screenshot.png', full_path], 
                          check=True)
            
            # Clean up screenshot from device
            subprocess.run(['adb', 'shell', 'rm', '/sdcard/screenshot.png'], 
                          check=True)
            
            print(f"Screenshot saved as: {full_path}")
            return full_path
            
        except subprocess.CalledProcessError as e:
            print(f"Error taking screenshot: {e}")
            return False
    
    def start_screen_recording(self, filename=None, duration=30):
        """Start screen recording from the Quest headset"""
        if not self.connected:
            print("Device not connected")
            return False
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quest_recording_{timestamp}.mp4"
        
        # Ensure filename has .mp4 extension
        if not filename.lower().endswith('.mp4'):
            filename += '.mp4'
            
        # Full path to output folder
        full_path = os.path.join(self.output_folder, filename)
        
        try:
            print(f"Starting screen recording for {duration} seconds...")
            
            # Start recording on device
            recording_process = subprocess.Popen([
                'adb', 'shell', 'screenrecord', 
                f'--time-limit={duration}', 
                '/sdcard/recording.mp4'
            ])
            
            # Wait for recording to complete
            recording_process.wait()
            
            # Pull recording to local machine
            print("Recording complete, downloading...")
            subprocess.run(['adb', 'pull', '/sdcard/recording.mp4', full_path], 
                          check=True)
            
            # Clean up recording from device
            subprocess.run(['adb', 'shell', 'rm', '/sdcard/recording.mp4'], 
                          check=True)
            
            print(f"Recording saved as: {full_path}")
            return full_path
            
        except subprocess.CalledProcessError as e:
            print(f"Error recording screen: {e}")
            return False
    
    def start_live_stream(self, fps=10):
        """Start a live stream of screenshots (basic implementation)"""
        if not self.connected:
            print("Device not connected")
            return False
        
        print(f"Starting live stream at {fps} FPS. Press Ctrl+C to stop.")
        print(f"Frames will be saved to: {self.output_folder}")
        self.streaming = True
        
        try:
            frame_count = 0
            while self.streaming:
                timestamp = datetime.now().strftime("%H:%M:%S")
                filename = f"frame_{frame_count:06d}.png"
                full_path = os.path.join(self.output_folder, filename)
                
                # Take screenshot
                subprocess.run(['adb', 'shell', 'screencap', '-p', '/sdcard/temp_frame.png'], 
                              check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Pull screenshot
                subprocess.run(['adb', 'pull', '/sdcard/temp_frame.png', full_path], 
                              check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                print(f"Frame {frame_count} captured at {timestamp}")
                frame_count += 1
                
                time.sleep(1.0 / fps)
                
        except KeyboardInterrupt:
            print("\nStopping live stream...")
            self.streaming = False
            
            # Clean up temp file
            subprocess.run(['adb', 'shell', 'rm', '/sdcard/temp_frame.png'], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def view_screen_realtime(self, fps=10, scale=0.5):
        """Display Quest screen in real-time using a GUI window"""
        if not GUI_AVAILABLE:
            print("Real-time viewer not available. Please install required packages:")
            print("pip install pillow")
            return False
            
        if not self.connected:
            print("Device not connected")
            return False
        
        # Create GUI window
        root = tk.Tk()
        root.title("Oculus Quest - Live View")
        root.configure(bg='black')
        
        # Create label for image display
        image_label = tk.Label(root, bg='black')
        image_label.pack(padx=10, pady=10)
        
        # Status label
        status_label = tk.Label(root, text="Initializing...", fg='white', bg='black')
        status_label.pack()
        
        # Control frame
        control_frame = tk.Frame(root, bg='black')
        control_frame.pack(pady=5)
        
        # FPS control
        fps_label = tk.Label(control_frame, text="FPS:", fg='white', bg='black')
        fps_label.pack(side=tk.LEFT, padx=5)
        
        fps_var = tk.StringVar(value=str(fps))
        fps_entry = tk.Entry(control_frame, textvariable=fps_var, width=5)
        fps_entry.pack(side=tk.LEFT, padx=5)
        
        # Scale control
        scale_label = tk.Label(control_frame, text="Scale:", fg='white', bg='black')
        scale_label.pack(side=tk.LEFT, padx=5)
        
        scale_var = tk.StringVar(value=str(scale))
        scale_entry = tk.Entry(control_frame, textvariable=scale_var, width=5)
        scale_entry.pack(side=tk.LEFT, padx=5)
        
        # Stop button
        def stop_viewing():
            self.streaming = False
            root.quit()
        
        stop_button = tk.Button(control_frame, text="Stop", command=stop_viewing, 
                               bg='red', fg='white')
        stop_button.pack(side=tk.LEFT, padx=10)
        
        # Variables for threading
        self.streaming = True
        current_image = [None]
        frame_count = [0]
        
        def capture_frames():
            """Background thread for capturing frames"""
            try:
                while self.streaming:
                    current_fps = float(fps_var.get()) if fps_var.get().replace('.', '').isdigit() else 10
                    current_scale = float(scale_var.get()) if scale_var.get().replace('.', '').isdigit() else 0.5
                    
                    # Take screenshot and get raw data
                    result = subprocess.run(['adb', 'shell', 'screencap', '-p'], 
                                          capture_output=True)
                    
                    if result.returncode == 0:
                        # Convert raw screenshot data to PIL Image
                        # Fix line ending issues with screencap -p
                        raw_data = result.stdout.replace(b'\r\n', b'\n')
                        
                        try:
                            img = Image.open(io.BytesIO(raw_data))
                            
                            # Scale image
                            if current_scale != 1.0:
                                new_width = int(img.width * current_scale)
                                new_height = int(img.height * current_scale)
                                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            
                            current_image[0] = img
                            frame_count[0] += 1
                            
                        except Exception as e:
                            print(f"Error processing image: {e}")
                    
                    time.sleep(1.0 / current_fps)
                    
            except Exception as e:
                print(f"Error in capture thread: {e}")
                self.streaming = False
        
        def update_display():
            """Update the GUI with the latest frame"""
            if current_image[0] and self.streaming:
                try:
                    # Convert PIL image to PhotoImage for tkinter
                    photo = ImageTk.PhotoImage(current_image[0])
                    image_label.configure(image=photo)
                    image_label.image = photo  # Keep a reference
                    
                    # Update status
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    status_text = f"Frame {frame_count[0]} - {timestamp} - {current_image[0].size[0]}x{current_image[0].size[1]}"
                    status_label.configure(text=status_text)
                    
                except Exception as e:
                    status_label.configure(text=f"Display error: {e}")
            
            if self.streaming:
                root.after(50, update_display)  # Update display every 50ms
        
        # Start capture thread
        capture_thread = threading.Thread(target=capture_frames, daemon=True)
        capture_thread.start()
        
        # Start display updates
        root.after(100, update_display)
        
        print(f"Starting real-time viewer at {fps} FPS, scale {scale}")
        print("Close the window or click 'Stop' to exit")
        
        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.streaming = False
            print("Real-time viewer stopped")
        
        return True
    
    def disconnect(self):
        """Disconnect from the device"""
        if self.device_ip:
            subprocess.run(['adb', 'disconnect', f'{self.device_ip}:{self.adb_port}'])
            print("Disconnected from device")
        self.connected = False

def main():
    """Main function with interactive menu"""
    print("Oculus Quest ADB Screen Capture Tool")
    print("=====================================")
    
    # Get connection method
    connection_type = input("Connect via (1) USB or (2) WiFi? Enter 1 or 2: ").strip()
    
    if connection_type == "2":
        device_ip = input("Enter Quest IP address: ").strip()
        capture = QuestADBCapture(device_ip=device_ip)
    else:
        capture = QuestADBCapture()
    
    # Connect to device
    if not capture.connect_device():
        print("Failed to connect to device")
        return
    
    # Get device info
    capture.get_device_info()
    
    print(f"\nAll captures will be saved to: {capture.output_folder}")
    
    # Interactive menu
    while True:
        print("\nOptions:")
        print("1. Take screenshot")
        print("2. Record screen (30 seconds)")
        print("3. Start live stream (save frames)")
        print("4. View screen in real-time")
        print("5. Get device info")
        print("6. Disconnect and exit")
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == "1":
            filename = input("Enter filename (or press Enter for auto): ").strip()
            if not filename:
                filename = None
            capture.take_screenshot(filename)
            
        elif choice == "2":
            filename = input("Enter filename (or press Enter for auto): ").strip()
            if not filename:
                filename = None
            duration = input("Enter duration in seconds (default 30): ").strip()
            duration = int(duration) if duration.isdigit() else 30
            capture.start_screen_recording(filename, duration)
            
        elif choice == "3":
            fps = input("Enter FPS (default 10): ").strip()
            fps = int(fps) if fps.isdigit() else 10
            capture.start_live_stream(fps)
            
        elif choice == "4":
            if not GUI_AVAILABLE:
                print("Real-time viewer not available. Please install: pip install pillow")
            else:
                fps = input("Enter FPS (default 10): ").strip()
                fps = int(fps) if fps.isdigit() else 10
                scale = input("Enter scale factor (default 0.5): ").strip()
                scale = float(scale) if scale.replace('.', '').isdigit() else 0.5
                capture.view_screen_realtime(fps, scale)
            
        elif choice == "5":
            capture.get_device_info()
            
        elif choice == "6":
            capture.disconnect()
            break
            
        else:
            print("Invalid choice. Please enter 1-6.")

if __name__ == "__main__":
    main()