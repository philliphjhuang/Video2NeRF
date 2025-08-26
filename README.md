# Video2NeRF: Video to Neural Radiance Field Conversion

## Description
This project, `Video2NeRF`, is a web-based application that leverages the power of NVIDIA's `instant-ngp` (Instant Neural Graphics Primitives) to convert video footage into a 3D NeRF (Neural Radiance Field) model. It automates the process of extracting frames from a video, running COLMAP for structure-from-motion to estimate camera poses, and then preparing the data for `instant-ngp` to generate a reconstructable 3D scene. The `video2mesh` component of the project is specifically designed to handle video input and produce a mesh-like representation that can be viewed interactively.

## Features
- **Video to NeRF Conversion**: Automatically converts input video files into a NeRF-compatible dataset.
- **COLMAP Integration**: Utilizes COLMAP for robust camera pose estimation from video frames.
- **Web Interface**: Provides a user-friendly web interface for uploading videos, monitoring processing, and viewing results.
- **Real-time Processing Feedback**: Offers real-time updates on the progress of the NeRF generation process.
- **Interactive 3D Viewer**: Allows users to interactively explore the generated 3D scene (mesh) in a web browser.

## Installation
To set up and run the Video2NeRF project, follow these steps:

### Prerequisites
- **Python 3.8+**: Ensure you have Python installed.
- **FFmpeg**: Install FFmpeg for video frame extraction.
- **COLMAP**: Download and install COLMAP. Make sure the `colmap.exe` (or equivalent executable on Linux/macOS) is accessible and its path is correctly configured in `video2nerf.py`.
- **NVIDIA GPU with CUDA**: `instant-ngp` requires an NVIDIA GPU with CUDA support.
- **instant-ngp**: Clone and build the `instant-ngp` repository from [https://github.com/NVlabs/instant-ngp](https://github.com/NVlabs/instant-ngp). The `instant-ngp` executable and its `scripts` directory are crucial for this project.

### Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/philliphjhuang/video2mesh.git # Replace with actual repo URL
   cd video2mesh
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Frontend Setup**:
   The frontend is a simple HTML/CSS/JavaScript application. No specific installation steps are required beyond having the files in the correct location.

4. **Configure Paths**:
   Open `video2mesh/video2nerf.py` and update the following paths to match your system:
   ```python
   COLMAP_PATH = r"D:\COLMAP\bin\colmap.exe"  # Your COLMAP path
   INSTANT_NGP_SCRIPTS = r"instant-ngp\scripts" # Your instant-ngp scripts path
   ```
   
   If you change the `PROJECT_ROOT` or `VENV_PYTHON_PATH` in `video2mesh/backend/app.py` you should update them as well.

## Usage
1. **Start the Backend Server**:
   ```bash
   cd video2mesh/backend
   python app.py
   ```

2. **Open the Web Interface**:
   Navigate to `http://127.0.0.1:5000` (or the address where your Flask app is running) in your web browser.

3. **Upload Video**:
   On the web interface, upload a video file. The backend will process the video, convert it to a NeRF dataset, and prepare it for viewing.

4. **View 3D Model**:
   Once processing is complete, you will be able to interactively view the generated 3D NeRF model (mesh) directly in your browser.

## Project Structure
```
simpleNeRF/
├── instant-ngp/                # NVIDIA's Instant Neural Graphics Primitives project
│   ├── scripts/                # Scripts used by instant-ngp, including colmap2nerf.py
│   └── instant-ngp.exe         # Executable for instant-ngp
├── video2mesh/
│   ├── backend/
│   │   ├── app.py              # Flask backend application
│   │   └── requirements.txt    # Python dependencies for the backend
│   ├── dataset/
│   │   └── my_video/           # Directory for processed video outputs and NeRF data
│   │       └── [VIDEO_NAME]/   # Output for each video (e.g., frames/, colmap_project/, colmap_text/, transforms.json)
│   ├── uploads/                # Temporarily stores uploaded video files
│   ├── index.html              # Frontend HTML file
│   ├── main.js                 # Frontend JavaScript for interactivity
│   ├── style.css               # Frontend CSS for styling
│   ├── video2nerf.py           # Python script for video to NeRF conversion using COLMAP and instant-ngp
│   └── run_viewer.py           # Python script to run the local interactive viewer
└── README.md                   # Overall project README (this file)
```
