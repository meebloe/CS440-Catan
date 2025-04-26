import subprocess
import os
import time
import sys

# Absolute path to the Unity executable
UNITY_EXECUTABLE = os.path.abspath(os.path.join("client", "CatanLearner.exe"))

# Server script
AI_SERVER_SCRIPT = os.path.join("server", "catan_ai.py")
TRAINING_SCRIPT = os.path.join("server", "train_from_logs.py")

# Timeout for each Unity game in seconds (only for training)
GAME_TIMEOUT = 360

def clear_game_logs():
    log_dir = os.path.abspath(os.path.join("client", "SelfPlayLogs"))
    if not os.path.exists(log_dir):
        print(f"[DEBUG] Log directory {log_dir} does not exist, creating...")
        os.makedirs(log_dir)

    for filename in os.listdir(log_dir):
        if filename.endswith(".jsonl"):
            file_path = os.path.join(log_dir, filename)
            os.remove(file_path)

    print("Cleared all game logs.")

def launch_ai_server(mode):
    print("Starting AI Server...")
    print(f"Launching AI Server in {mode.upper()} mode...")  # <-- This new printout
    env_name = os.environ.get("CONDA_DEFAULT_ENV")
    if env_name != "catan_ai_env":
        print(f"ERROR: Please activate 'catan_ai_env' before running this script (current: {env_name})")
        sys.exit(1)

    env = os.environ.copy()
    env["CATAN_TRAIN_MODE"] = "1" if mode == "train" else "0"

    return subprocess.Popen(["python", AI_SERVER_SCRIPT], env=env)

def launch_game(mode):
    if mode == "train":
        print("Launching Unity Game in Bot vs Bot Mode...")
        bot_mode_arg = "--bot-vs-bot"
    else:
        print("Launching Unity Game in Human vs Bot Mode...")
        bot_mode_arg = ""

    command = f'"{UNITY_EXECUTABLE}" {bot_mode_arg}'.strip()
    return subprocess.Popen(command, shell=True)

def train_model(mode):
    print(f"Starting training from game logs in {mode.upper()} mode...")
    result = subprocess.run(["python", TRAINING_SCRIPT, mode])
    if result.returncode == 0:
        print("Training completed successfully.\n")
    else:
        print("Training failed.\n")

def shutdown(server_proc):
    print("Shutting down AI Server...")
    try:
        server_proc.terminate()
        server_proc.wait(timeout=10)
    except Exception as e:
        print(f"Failed to cleanly shut down server: {e}")

if __name__ == "__main__":
    mode = "play"
    num_games = 1

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    if len(sys.argv) > 2 and mode == "train":
        try:
            num_games = int(sys.argv[2])
        except ValueError:
            print("Invalid number of games. Must be an integer.")
            sys.exit(1)

    if mode not in {"train", "play"}:
        print("Invalid mode. Use 'train' or 'play'.")
        sys.exit(1)

    clear_game_logs()

    server_proc = launch_ai_server(mode)
    time.sleep(3)

    try:
        if mode == "train":
            for game_num in range(1, num_games + 1):
                print(f"Starting training game {game_num} of {num_games}...")
                game_proc = launch_game(mode)
                try:
                    game_proc.wait(timeout=GAME_TIMEOUT)
                    print(f"Training game {game_num} finished successfully.\n")
                except subprocess.TimeoutExpired:
                    print(f"Training game {game_num} timed out after {GAME_TIMEOUT // 60} minutes. Force closing and moving to next...\n")
                    game_proc.kill()
                    game_proc.wait()
            train_model("train")
        else:
            print("Starting play mode...")
            game_proc = launch_game(mode)
            game_proc.wait()
            train_model("play")

    finally:
        shutdown(server_proc)