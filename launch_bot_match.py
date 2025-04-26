import subprocess
import os
import time
import sys

# Absolute path to the Unity executable
UNITY_EXECUTABLE = os.path.abspath(os.path.join("client", "CatanLearner.exe"))

# Server script
AI_SERVER_SCRIPT = os.path.join("server", "catan_ai.py")
TRAINING_SCRIPT = os.path.join("server", "train_from_logs.py")
ITERATIONS_FOLDER = os.path.join("server", "iterations")
MODEL_PATH = os.path.join("server", "model_weights.pth")
VALID_MODES = {"train", "play", "bulktrain"}

def clear_game_logs():
    log_dir = os.path.abspath(os.path.join("client", "SelfPlayLogs"))
    old_logs_dir = os.path.abspath(os.path.join("client", "OldLogs"))

    if not os.path.exists(log_dir):
        print(f"[DEBUG] Log directory {log_dir} does not exist, creating...")
        os.makedirs(log_dir)

    if not os.path.exists(old_logs_dir):
        print(f"[DEBUG] Old logs directory {old_logs_dir} does not exist, creating...")
        os.makedirs(old_logs_dir)

    # Move existing logs to OldLogs
    for filename in os.listdir(log_dir):
        if filename.endswith(".jsonl"):
            source_path = os.path.join(log_dir, filename)
            dest_path = os.path.join(old_logs_dir, filename)
            try:
                os.rename(source_path, dest_path)
                print(f"Moved {filename} to OldLogs.")
            except Exception as e:
                print(f"Failed to move {filename}: {e}")

    print("Cleared all game logs (moved to OldLogs).")

def launch_ai_server(mode):
    print("Starting AI Server...")
    print(f"Launching AI Server in {mode.upper()} mode...")
    env_name = os.environ.get("CONDA_DEFAULT_ENV")

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

def launch_bulk_train(x_games, y_sets):
    os.makedirs(ITERATIONS_FOLDER, exist_ok=True)

    for set_num in range(y_sets):
        print(f"=== Starting Set {set_num + 1} / {y_sets} ===")
        
        # Launch X games
        processes = []
        for _ in range(x_games):
            command = f'"{UNITY_EXECUTABLE}" --bot-vs-bot'.strip()
            proc = subprocess.Popen(command, shell=True)
            processes.append(proc)

        for proc in processes:
            proc.wait()

        print("[INFO] All games done. Training...")

        # Train
        subprocess.run([sys.executable, TRAINING_SCRIPT])

        # Save model
        save_model_checkpoint()

        # Clear logs after training
        clear_game_logs()

    print("\n[INFO] Bulk training completed.")

def save_model_checkpoint():
    existing = os.listdir(ITERATIONS_FOLDER)
    n_models = sum(1 for f in existing if f.startswith("settlerbot_") and f.endswith(".pth"))

    save_name = f"settlerbot_{n_models}.pth"
    save_path = os.path.join(ITERATIONS_FOLDER, save_name)

    shutil.copy(MODEL_PATH, save_path)


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

    if mode not in {"train", "play", "bulktrain"}:
        print("Invalid mode. Use 'train' or 'play'.")
        sys.exit(1)

    clear_game_logs()

    server_proc = launch_ai_server(mode)
    time.sleep(3)

    try:
        if mode == "bulktrain":
            x_games = int(sys.argv[2])
            y_sets = int(sys.argv[3])
            launch_bulk_train(x_games, y_sets)

        elif mode == "train":
            game_procs = []
            for game_num in range(1, num_games + 1):
                print(f"Starting training game {game_num} of {num_games}...")
                proc = launch_game(mode)
                game_procs.append(proc)
            
            print("Waiting for all games to finish...")
            for proc in game_procs:
                proc.wait()

            train_model("train")
        else:
            print("Starting play mode...")
            game_proc = launch_game(mode)
            game_proc.wait()
            train_model("play")

    finally:
        shutdown(server_proc)