import os
import subprocess
import sys
import argparse # Import argparse
import json # Import json for post-processing
from dotenv import load_dotenv # Import load_dotenv

# ===========================
# USER SETTINGS
# ===========================
# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Parse command line arguments
parser = argparse.ArgumentParser(description="Run video2nerf process.")
parser.add_argument('--video_path', type=str, required=True, help='Path to the input video file.')
parser.add_argument('--output_dir', type=str, default=os.path.join(os.path.dirname(__file__), "output"), help='Directory to save output files.') # Set default output_dir
parser.add_argument('--fps', type=int, default=4, help='Frames per second to extract from the video.')
args = parser.parse_args()

VIDEO_PATH = args.video_path
OUTPUT_DIR = args.output_dir
FPS = args.fps

COLMAP_PATH = os.getenv("COLMAP_PATH")  # <-- your COLMAP path
INSTANT_NGP_SCRIPTS = os.getenv("INSTANT_NGP_SCRIPTS")

# ===========================
# HELPER FUNCTIONS
# ===========================
def run(cmd):
    print(f"\n>>> Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(1)

# ===========================
# 1. Extract frames
# ===========================
frames_dir = os.path.join(OUTPUT_DIR, "frames")
os.makedirs(frames_dir, exist_ok=True)

run(f'ffmpeg -i "{VIDEO_PATH}" -q:v 2 -vf "fps={FPS}" "{frames_dir}\\frame_%04d.jpg"')

# ===========================
# 2. Run COLMAP automatic reconstruction
# ===========================
colmap_project = os.path.join(OUTPUT_DIR, "colmap_project")
os.makedirs(colmap_project, exist_ok=True)

run(f'"{COLMAP_PATH}" automatic_reconstructor --workspace_path "{colmap_project}" --image_path "{frames_dir}" --quality low')

# ===========================
# 3. Export sparse model to text format
# ===========================
colmap_sparse = os.path.join(colmap_project, "sparse", "0")
colmap_text = os.path.join(OUTPUT_DIR, "colmap_text")
os.makedirs(colmap_text, exist_ok=True)

run(f'"{COLMAP_PATH}" model_converter --input_path "{colmap_sparse}" --output_path "{colmap_text}" --output_type TXT')

# ===========================
# 4. Run colmap2nerf.py
# ===========================
colmap2nerf_script = os.path.join(INSTANT_NGP_SCRIPTS, "colmap2nerf.py")

# Make sure colmap2nerf.py points to correct TEXT_FOLDER
with open(colmap2nerf_script, "r") as f:
    content = f.read()
content = content.replace('TEXT_FOLDER = r"D:\VScode\Code\simpleNeRF\dataset\my_video\output\colmap_text"', f'TEXT_FOLDER = r"{colmap_text}"')
with open(colmap2nerf_script, "w") as f:
    f.write(content)

transforms_out = os.path.join(frames_dir, "transforms.json")
run(f'python "{colmap2nerf_script}" --colmap_db "{os.path.join(colmap_project, "database.db")}" --images "{frames_dir}" --text "{colmap_text}" --out "{transforms_out}"')

print("\nAll done! Open this folder in instant-ngp.exe (NeRF mode):")
print(frames_dir)

# Post-process transforms.json to simplify file paths
try:
    with open(transforms_out, 'r') as f:
        transforms_data = json.load(f)

    for frame in transforms_data['frames']:
        # Extract only the filename from the file_path
        frame['file_path'] = os.path.basename(frame['file_path'])

    with open(transforms_out, 'w') as f:
        json.dump(transforms_data, f, indent=2)
    
    print(f"[Post-processing] transforms.json updated successfully.")
except Exception as e:
    print(f"[Post-processing Error] Failed to post-process transforms.json: {e}")
