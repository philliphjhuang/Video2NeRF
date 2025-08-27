from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import os
import subprocess
import threading
import queue
import time
import uuid
import json
import numpy as np
import math
from ffprobe import FFProbe

os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin")

# Get the absolute path to the project root (D:\VScode\Code\simpleNeRF)
# Assuming app.py is in Video2NeRF/backend/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
VENV_PYTHON_PATH = os.path.join(PROJECT_ROOT, 'Video2NeRF', 'venv', 'Scripts', 'python.exe')

app = Flask(__name__, static_folder=os.path.join(PROJECT_ROOT, 'Video2NeRF'))
CORS(app) # Enable CORS for all routes

UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Base directory for storing NeRF datasets (frames, transforms.json, snapshots, videos)
dataset_base_dir = os.path.join(PROJECT_ROOT, 'Video2NeRF', 'dataset', 'my_video') # Updated path
if not os.path.exists(dataset_base_dir):
    os.makedirs(dataset_base_dir)

PROCESSING_STATUS = {}

# Queue for capturing script output
output_queue = queue.Queue()

def run_script_in_background(video_path, output_dir, fps, task_id, original_filename):
    script_path = os.path.join(PROJECT_ROOT, 'Video2NeRF', 'video2nerf.py') # Updated path
    command = [
        VENV_PYTHON_PATH, script_path,
        '--video_path', video_path,
        '--output_dir', output_dir,
        '--fps', str(fps)
    ]
    
    PROCESSING_STATUS[task_id] = {'status': 'started', 'progress': 0, 'output': [], 'video_original_name': original_filename}

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    for line in iter(process.stdout.readline, ''):
        print(f"[video2nerf] {line.strip()}") # Added logging for subprocess output
        PROCESSING_STATUS[task_id]['output'].append(line.strip())
        # Here you might parse the line to update a more meaningful progress
        if "Extract frames" in line:
            PROCESSING_STATUS[task_id]['progress'] = 20
        elif "Run COLMAP automatic reconstruction" in line:
            PROCESSING_STATUS[task_id]['progress'] = 40
        elif "Export sparse model to text format" in line:
            PROCESSING_STATUS[task_id]['progress'] = 60
        elif "Run colmap2nerf.py" in line:
            PROCESSING_STATUS[task_id]['progress'] = 80
        elif "All done!" in line:
            PROCESSING_STATUS[task_id]['progress'] = 100
            PROCESSING_STATUS[task_id]['status'] = 'completed'
        
        output_queue.put({'task_id': task_id, 'line': line.strip(), 'progress': PROCESSING_STATUS[task_id]['progress']})

    process.wait()
    if process.returncode != 0:
        PROCESSING_STATUS[task_id]['status'] = 'failed'
        output_queue.put({'task_id': task_id, 'line': f"Script failed with exit code {process.returncode}", 'progress': PROCESSING_STATUS[task_id]['progress']})
    else:
        PROCESSING_STATUS[task_id]['status'] = 'video2nerf_completed'
        output_queue.put({'task_id': task_id, 'line': "Video2NeRF completed successfully", 'progress': 100})

        # Now, trigger NeRF training
        train_nerf_model(output_dir, task_id)

def train_nerf_model(output_dir, task_id):
    # Revert changes related to DLL path management
    run_script_path = os.path.join(PROJECT_ROOT, 'instant-ngp', 'scripts', 'run.py')
    snapshot_path = os.path.join(output_dir, 'trained.ingp')
    train_steps = 2000 # You might want to make this configurable

    train_command = [
        VENV_PYTHON_PATH, run_script_path,
        '--scene', os.path.join(output_dir, "frames"), # Explicitly pass output_dir/frames as --scene
        '--n_steps', str(train_steps),
        '--save_snapshot', snapshot_path
    ]

    PROCESSING_STATUS[task_id]['status'] = 'training_started'
    PROCESSING_STATUS[task_id]['progress'] = 0
    output_queue.put({'task_id': task_id, 'line': "NeRF training started", 'progress': 0, 'status': 'training_started'})

    # Log the command for debugging
    # print(f"[NeRF Training] Scene path: {output_dir}")
    # transforms_json_path = os.path.join(output_dir, 'transforms.json')
    # if os.path.exists(transforms_json_path):
    #     print(f"[NeRF Training] transforms.json found at: {transforms_json_path}")
    #     try:
    #         with open(transforms_json_path, 'r') as f:
    #             transforms_content = json.load(f)
    #             print(f"[NeRF Training] transforms.json content (first 500 chars): {str(transforms_content)[:500]}...")
    #     except Exception as e:
    #         print(f"[NeRF Training] Error reading transforms.json: {e}")
    # else:
    #     print(f"[NeRF Training] WARNING: transforms.json NOT FOUND at: {transforms_json_path}")
    print(f"[NeRF Training] Executing command: {' '.join(train_command)}")

    # Prepare environment for subprocess, explicitly including CUDA bin to PATH
    env = os.environ.copy()
    cuda_bin_path = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin"
    if "PATH" in env:
        env["PATH"] = f"{cuda_bin_path};{env["PATH"]}"
    else:
        env["PATH"] = cuda_bin_path

    train_process = subprocess.Popen(train_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

    for line in iter(train_process.stdout.readline, ''):
        print(f"[NeRF Training] {line.strip()}") # Added logging for subprocess output
        PROCESSING_STATUS[task_id]['output'].append(line.strip())
        # Basic progress parsing for training
        if "PROGRESS" in line:
            try:
                progress_str = line.split('%')[0].strip().split()[-1]
                progress = int(progress_str)
                PROCESSING_STATUS[task_id]['progress'] = progress
            except (ValueError, IndexError):
                pass
        output_queue.put({'task_id': task_id, 'line': line.strip(), 'progress': PROCESSING_STATUS[task_id]['progress'], 'status': 'training_in_progress'})

    train_process.wait()
    if train_process.returncode != 0:
        PROCESSING_STATUS[task_id]['status'] = 'training_failed'
        output_queue.put({'task_id': task_id, 'line': f"NeRF training failed with exit code {train_process.returncode}", 'progress': PROCESSING_STATUS[task_id]['progress'], 'status': 'training_failed'})
    else:
        PROCESSING_STATUS[task_id]['status'] = 'training_completed'
        output_queue.put({'task_id': task_id, 'line': "NeRF training completed successfully", 'progress': 100, 'status': 'training_completed'})
        PROCESSING_STATUS[task_id]['snapshot_path'] = snapshot_path
        # After training, proceed to generate camera path
        generate_camera_path(output_dir, task_id)

def generate_camera_path(output_dir, task_id, num_frames=60, radius=1.5):
    camera_path = {
        "camera_path": [],
        "render_fov": 45,
        "render_width": 1280,
        "render_height": 720,
        "fps": 30,
        "shutter_speed": 1000,
        "exposure": 1.0
    }

    # Generate a circular path around the origin
    for i in range(num_frames):
        angle = 2 * math.pi * i / num_frames
        x = radius * math.sin(angle)
        y = radius * math.cos(angle)
        # Add vertical oscillation
        z = 0.5 + 0.2 * math.sin(4 * math.pi * i / num_frames) # Oscillation in Z-axis

        # Camera position (add slight radius variation)
        current_radius = radius + 0.1 * math.sin(2 * math.pi * i / num_frames)
        position = np.array([current_radius * math.sin(angle), current_radius * math.cos(angle), z])

        # Look-at point (origin)
        look_at = np.array([0.0, 0.0, 0.0])

        # Up vector (standard +Y or +Z depending on coordinate system)
        up_vector = np.array([0.0, 0.0, 1.0]) # Assuming Z-up

        # Calculate rotation matrix
        # Z-axis of camera points from position to look_at
        camera_z = (look_at - position)
        camera_z = camera_z / np.linalg.norm(camera_z)

        # X-axis of camera is cross product of up and camera_z
        camera_x = np.cross(up_vector, camera_z)
        camera_x = camera_x / np.linalg.norm(camera_x)

        # Y-axis of camera is cross product of camera_z and camera_x
        camera_y = np.cross(camera_z, camera_x)
        camera_y = camera_y / np.linalg.norm(camera_y)

        # Construct 3x3 rotation matrix (camera-to-world)
        R = np.vstack([camera_x, camera_y, camera_z]).T

        # Construct 4x4 transformation matrix (camera-to-world)
        transform_matrix = np.eye(4)
        transform_matrix[:3, :3] = R
        transform_matrix[:3, 3] = position

        camera_path["camera_path"].append({
            "camera_to_world": transform_matrix.tolist()
        })
    
    camera_path_file = os.path.join(output_dir, "base_cam.json")
    with open(camera_path_file, 'w') as f:
        json.dump(camera_path, f, indent=4)
    
    PROCESSING_STATUS[task_id]['camera_path_file'] = camera_path_file
    PROCESSING_STATUS[task_id]['status'] = 'camera_path_generated'
    output_queue.put({'task_id': task_id, 'line': "Camera path generated successfully", 'progress': 100, 'status': 'camera_path_generated'})

    # After camera path generation, proceed to video rendering
    render_nerf_video(PROCESSING_STATUS[task_id]['snapshot_path'], camera_path_file, output_dir, task_id)

def render_nerf_video(snapshot_path, camera_path_file, output_dir, task_id):
    run_script_path = os.path.join(PROJECT_ROOT, 'instant-ngp', 'scripts', 'run.py')
    output_video_path = os.path.join(output_dir, 'output_video.mp4')
    video_fps = 30 # From base_cam.json, but can be configured
    width = 1280 # From base_cam.json, but can be configured
    height = 720 # From base_cam.json, but can be configured

    render_command = [
        VENV_PYTHON_PATH, run_script_path,
        snapshot_path,
        '--n_steps', '0', # Explicitly set n_steps to 0 to prevent training during rendering
        '--video_camera_path', camera_path_file,
        '--video_n_seconds', '5', # Render a 5-second video
        '--video_fps', str(video_fps),
        '--width', str(width),
        '--height', str(height),
        '--video_output', output_video_path
    ]

    PROCESSING_STATUS[task_id]['status'] = 'rendering_started'
    PROCESSING_STATUS[task_id]['progress'] = 0
    output_queue.put({'task_id': task_id, 'line': "Video rendering started", 'progress': 0, 'status': 'rendering_started'})

    render_process = subprocess.Popen(render_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    for line in iter(render_process.stdout.readline, ''):
        print(f"[NeRF Rendering] {line.strip()}") # Added logging for subprocess output
        PROCESSING_STATUS[task_id]['output'].append(line.strip())
        if "PROGRESS" in line:
            try:
                progress_str = line.split('%')[0].strip().split()[-1]
                progress = int(progress_str)
                PROCESSING_STATUS[task_id]['progress'] = progress
            except (ValueError, IndexError):
                pass
        output_queue.put({'task_id': task_id, 'line': line.strip(), 'progress': PROCESSING_STATUS[task_id]['progress'], 'status': 'rendering_in_progress'})

    render_process.wait()
    if render_process.returncode != 0:
        PROCESSING_STATUS[task_id]['status'] = 'rendering_failed'
        output_queue.put({'task_id': task_id, 'line': f"Video rendering failed with exit code {render_process.returncode}", 'progress': PROCESSING_STATUS[task_id]['progress'], 'status': 'rendering_failed'})
    else:
        PROCESSING_STATUS[task_id]['status'] = 'completed' # Final status for the entire process
        output_queue.put({'task_id': task_id, 'line': "Video rendering completed successfully", 'progress': 100, 'status': 'completed'})
        PROCESSING_STATUS[task_id]['output_video_path'] = output_video_path
        print(f"Rendered video saved to: {output_video_path}")

@app.route('/video_result/<task_id>')
def serve_rendered_video(task_id):
    if task_id not in PROCESSING_STATUS or 'output_video_path' not in PROCESSING_STATUS[task_id]:
        return "Video not found or still processing", 404
    
    video_path = PROCESSING_STATUS[task_id]['output_video_path']
    video_dir = os.path.dirname(video_path)
    video_filename = os.path.basename(video_path)

    # Security check to prevent directory traversal
    if not os.path.abspath(video_dir).startswith(os.path.abspath(dataset_base_dir)):
        return "Forbidden", 403

    return send_from_directory(video_dir, video_filename, mimetype='video/mp4')

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file part'}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected video file'}), 400
    if file:
        filename = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filename)
        return jsonify({'message': 'Video uploaded successfully', 'filename': filename}), 200

@app.route('/process_video', methods=['POST'])
def process_video():
    data = request.get_json()
    filename = data.get('filename')
    quality = data.get('quality')

    if not filename or not quality:
        return jsonify({'error': 'Missing filename or quality'}), 400

    video_path = os.path.join(UPLOAD_FOLDER, os.path.basename(filename)) # Ensure filename is just the name, not full path
    
    # Map quality to FPS
    fps_map = {
        'low': 2,
        'normal': 4,
        'high': 6
    }
    fps = fps_map.get(quality, 4) # Default to normal if not found

    # Create a unique output directory for each processing task
    task_id = str(uuid.uuid4())
    output_base_name = os.path.splitext(os.path.basename(video_path))[0]
    specific_output_dir = os.path.join(dataset_base_dir, output_base_name + '_' + task_id)
    os.makedirs(specific_output_dir, exist_ok=True)

    threading.Thread(target=run_script_in_background, args=(video_path, specific_output_dir, fps, task_id, os.path.basename(filename))).start()
    
    return jsonify({'message': 'Video processing started', 'task_id': task_id}), 200

@app.route('/progress/<task_id>')
def get_progress(task_id):
    def generate_progress():
        last_progress_line_idx = 0
        while True:
            if task_id in PROCESSING_STATUS:
                current_status = PROCESSING_STATUS[task_id]
                new_output_lines = current_status['output'][last_progress_line_idx:]
                for line in new_output_lines:
                    yield f"data: {json.dumps({'line': line, 'progress': current_status['progress'], 'status': current_status['status']})}\n\n"
                last_progress_line_idx = len(current_status['output'])

                if current_status['status'] in ['completed', 'failed']:
                    yield f"data: {json.dumps({'line': 'Processing finished.', 'progress': current_status['progress'], 'status': current_status['status']})}\n\n"
                    break
            time.sleep(1) # Poll every second
    return Response(generate_progress(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)
