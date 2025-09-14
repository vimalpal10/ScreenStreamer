# Overview

This is a Windows 10 Screen Recorder application built with Python that provides a GUI-based tool for capturing screen recordings with audio. The application features a Tkinter-based interface that allows users to record their screen in various quality settings (HD, Full HD, 4K) with optional audio capture from microphones. The recorder outputs MP4 files with timestamps and supports pause/resume functionality during recording sessions.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Desktop Application Framework
- **GUI Framework**: Tkinter for the main user interface with ttk for modern styling
- **Threading Model**: Multi-threaded architecture separating GUI operations from recording tasks to maintain responsiveness
- **Recording Engine**: OpenCV (cv2) for video capture and frame processing
- **Audio Processing**: PyAudio for real-time audio capture and WAV file generation

## Video Recording Architecture
- **Screen Capture**: PyAutoGUI for screenshot-based frame capture with fallback mock implementation for headless environments
- **Video Encoding**: OpenCV VideoWriter with MP4V codec for real-time video file creation
- **Quality Scaling**: Dynamic resolution adjustment based on user selection (720p, 1080p, 4K) with automatic screen size detection
- **Frame Processing**: NumPy arrays for efficient image data manipulation and format conversion

## Audio-Video Synchronization
- **Separate Recording Streams**: Independent video and audio recording threads for better performance
- **Post-Processing Muxing**: MoviePy integration for combining separate video and audio files into final MP4 output
- **Audio Formats**: WAV intermediate format for audio capture with MP4 final output

## File Management System
- **Automatic Naming**: Timestamp-based file naming convention (screen_recording_YYYYMMDD_HHMMSS.mp4)
- **Output Organization**: Files saved in application directory with user feedback on save location
- **Temporary File Handling**: Intermediate audio/video files managed during the muxing process

## Error Handling and Environment Adaptation
- **Graceful Degradation**: Mock implementations for components that fail in headless environments
- **Import Protection**: Try-catch blocks around optional dependencies like MoviePy
- **Cross-Environment Support**: Code designed to run in both development (Replit) and production (Windows 10) environments

# External Dependencies

## Core Recording Libraries
- **OpenCV (cv2)**: Computer vision library for video capture, encoding, and frame manipulation
- **PyAutoGUI**: Screen capture and automation library for taking screenshots
- **PyAudio**: Real-time audio I/O library for microphone input capture
- **NumPy**: Numerical computing library for efficient array operations on image data

## Media Processing
- **MoviePy**: Video editing library for audio-video synchronization and final MP4 generation
- **Pillow (PIL)**: Python Imaging Library for image format conversions and mock screenshot generation
- **ImageIO-FFmpeg**: FFmpeg backend for MoviePy video processing operations

## GUI and System Integration
- **Tkinter**: Built-in Python GUI framework for the main application interface
- **Threading**: Python standard library for concurrent recording operations
- **Wave**: Python standard library for WAV audio file handling

## Build and Distribution
- **PyInstaller**: Application packaging tool for creating standalone Windows executables
- **Standard Libraries**: datetime, os, time for file management and timing operations