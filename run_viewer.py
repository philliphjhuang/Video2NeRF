import os
import subprocess
import sys

# --- USER CONFIGURATION ---
# IMPORTANT: Replace this with the actual path to your generated 'frames' directory.
# Example: r"D:\VScode\Code\simpleNeRF\video2mesh\dataset\my_video\Hamster_98cb8e5a-ab94-4fe5-b2f0-2a7650aeb9fc\frames"
SCENE_PATH = r"dataset\my_video\Hamster_443a693e-42a4-4d10-9481-cf9701bffc84\frames"
# --- END USER CONFIGURATION ---


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VENV_PYTHON_PATH = os.path.join(PROJECT_ROOT, 'video2mesh', 'venv', 'Scripts', 'python.exe')
INSTANT_NGP_RUN_SCRIPT = os.path.join(PROJECT_ROOT, 'instant-ngp', 'scripts', 'run.py')

if not os.path.exists(SCENE_PATH):
    print(f"Error: SCENE_PATH does not exist: {SCENE_PATH}")
    print("Please update the SCENE_PATH variable in this script (run_viewer.py) to your actual frames directory.")
    sys.exit(1)

if not os.path.exists(VENV_PYTHON_PATH):
    print(f"Error: Python virtual environment not found at: {VENV_PYTHON_PATH}")
    print("Please ensure your virtual environment is correctly set up or update VENV_PYTHON_PATH in this script.")
    sys.exit(1)

if not os.path.exists(INSTANT_NGP_RUN_SCRIPT):
    print(f"Error: instant-ngp/scripts/run.py not found at: {INSTANT_NGP_RUN_SCRIPT}")
    print("Please ensure the instant-ngp repository is correctly located.")
    sys.exit(1)

command = [
    VENV_PYTHON_PATH,
    INSTANT_NGP_RUN_SCRIPT,
    SCENE_PATH,
    # '--gui' # Removed --gui flag for headless operation
    '--n_steps', '2000', # Add --n_steps for headless training
    '--save_snapshot', os.path.join(SCENE_PATH, 'trained.ingp') # Add --save_snapshot
]

# Explicitly add CUDA bin to PATH for the subprocess
env = os.environ.copy()
cuda_bin_path = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin"
if "PATH" in env:
    env["PATH"] = f"{cuda_bin_path};{env["PATH"]}"
else:
    env["PATH"] = cuda_bin_path

print(f"Executing command: {' '.join(command)}")

try:
    # Using subprocess.run for simpler execution; for long-running processes, Popen might be used.
    result = subprocess.run(command, env=env, check=True, text=True, capture_output=True)
    print("\n--- stdout ---")
    print(result.stdout)
    print("\n--- stderr ---")
    print(result.stderr)
except subprocess.CalledProcessError as e:
    print(f"\nError running instant-ngp: {e}")
    print("\n--- stdout ---")
    print(e.stdout)
    print("\n--- stderr ---")
    print(e.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)
