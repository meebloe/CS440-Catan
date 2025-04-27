# launch_bot_match.py

import subprocess
import os
import time
import sys
import shutil
# import signal # Required for process group killing if needed later

# --- Constants and Paths ---
UNITY_EXECUTABLE = os.path.abspath(os.path.join("client", "CatanLearner.exe"))
AI_SERVER_SCRIPT = os.path.join("server", "catan_ai.py")
TRAINING_SCRIPT = os.path.join("server", "train_from_logs.py")
ITERATIONS_FOLDER = os.path.join("server", "iterations")
MODEL_PATH = os.path.join("server", "model_weights.pth")
VALID_MODES = {"train", "play", "bulktrain"}
# --- Timeout Constant - SET THIS AS NEEDED ---
MAX_GAME_DURATION_SECONDS = 180 # Set to 3 minutes (180 seconds)
# --- End Constants ---


# --- Helper Functions (clear_game_logs, launch_ai_server, etc.) ---
# Assume previous versions of clear_game_logs, launch_ai_server, train_model,
# shutdown, save_model_checkpoint are here, unchanged unless noted below.
# ... (Functions from previous version omitted for brevity) ...

def clear_game_logs():
    """Moves existing .jsonl logs from SelfPlayLogs to OldLogs with timestamps."""
    log_dir = os.path.abspath(os.path.join("client", "SelfPlayLogs"))
    old_logs_dir = os.path.abspath(os.path.join("client", "OldLogs"))
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(old_logs_dir, exist_ok=True)
    moved_count = 0
    try:
        for filename in os.listdir(log_dir):
            if filename.endswith(".jsonl"):
                source_path = os.path.join(log_dir, filename)
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                base, ext = os.path.splitext(filename)
                dest_filename = f"{base}_{timestamp}{ext}"
                dest_path = os.path.join(old_logs_dir, dest_filename)
                try:
                    os.rename(source_path, dest_path)
                    moved_count += 1
                except Exception as e:
                    print(f"[Error] Failed to move log file {filename}: {e}")
        if moved_count > 0: print(f"[Info] Moved {moved_count} log file(s) to OldLogs.")
        else: print("[Info] No logs found in SelfPlayLogs to move.")
    except FileNotFoundError: print(f"[Info] Log directory {log_dir} not found during clearing.")
    except Exception as e: print(f"[Error] An error occurred during log clearing: {e}")

def launch_ai_server(mode):
    """Starts the Python Flask AI server."""
    print("[Info] Starting AI Server...")
    print(f"[Info] Launching AI Server in {mode.upper()} mode...")
    env_name = os.environ.get("CONDA_DEFAULT_ENV")
    if "catan_ai_env" not in (env_name or ""): print(f"[Warning] Conda environment 'catan_ai_env' might not be active (current: {env_name})")
    env = os.environ.copy()
    env["CATAN_TRAIN_MODE"] = "1" if mode == "train" or mode == "bulktrain" else "0"
    try:
        server_process = subprocess.Popen([sys.executable, AI_SERVER_SCRIPT], env=env)
        print(f"[Info] AI Server started with PID: {server_process.pid}")
        return server_process
    except FileNotFoundError: print(f"[Error] AI Server script not found at: {AI_SERVER_SCRIPT}"); return None
    except Exception as e: print(f"[Error] Failed to launch AI Server: {e}"); return None

def launch_game(mode):
    """Launches the Unity game executable with arguments as a list (shell=False)."""
    headless_flags = []
    bot_mode_flags = []

    if mode == "train" or mode == "bulktrain":
        #headless_flags = ["-batchmode", "-nographics"]
        bot_mode_flags = ["--bot-vs-bot"] # Assumes Unity uses this flag
    elif mode == "play":
        # bot_mode_flags = ["--human-vs-bot"] # Add if needed
        pass
    else:
        print(f"[Warning] Unknown mode '{mode}' passed to launch_game.")

    # --- Construct command list ---
    command_list = [UNITY_EXECUTABLE] # Start with the executable path
    command_list.extend(bot_mode_flags)
    command_list.extend(headless_flags)
    # ---

    print(f"[Info] Attempting to execute Unity command list: {command_list}")
    try:
        # --- Use shell=False (default) and pass the list ---
        game_process = subprocess.Popen(command_list)
        # ---
        print(f"[Info] Launched game process with PID: {game_process.pid}")
        return game_process
    except FileNotFoundError:
         print(f"[Error] Unity executable not found at: {UNITY_EXECUTABLE}")
         print("[Error] Please ensure the path is correct and the file exists.")
         return None
    except Exception as e:
        # Provide more detail if possible, e.g., permission errors
        print(f"[Error] Failed to launch Unity game process: {e}")
        return None

def train_model(mode):
    """Runs the training script using the logs generated."""
    print(f"[Info] Starting training from game logs in {mode.upper()} mode...")
    try:
        result = subprocess.run([sys.executable, TRAINING_SCRIPT, mode], check=False)
        if result.returncode == 0: print("[Info] Training completed successfully.\n")
        else: print(f"[Warning] Training script exited with code {result.returncode}.\n")
    except FileNotFoundError: print(f"[Error] Training script not found at: {TRAINING_SCRIPT}")
    except Exception as e: print(f"[Error] An error occurred during training: {e}")

def shutdown(server_proc):
    """Attempts to gracefully terminate the AI server process."""
    if server_proc and server_proc.poll() is None:
        print("[Info] Shutting down AI Server...")
        try:
            server_proc.terminate()
            server_proc.wait(timeout=10)
            print("[Info] AI Server shut down.")
        except subprocess.TimeoutExpired: print("[Warning] AI Server did not terminate gracefully, killing."); server_proc.kill()
        except Exception as e: print(f"[Error] Error shutting down server: {e}")
    else: print("[Info] No active AI server process found or already terminated.")

def save_model_checkpoint(set_num):
    """Saves a numbered checkpoint copy of the current model weights."""
    if not os.path.exists(MODEL_PATH): print(f"[Warning] Main model file {MODEL_PATH} not found. Cannot create checkpoint."); return
    os.makedirs(ITERATIONS_FOLDER, exist_ok=True)
    save_name = f"settlerbot_{set_num}.pth"
    save_path = os.path.join(ITERATIONS_FOLDER, save_name)
    try:
        shutil.copy2(MODEL_PATH, save_path)
        print(f"[Info] Saved model checkpoint to {save_path}")
    except Exception as e: print(f"[Error] Failed to save model checkpoint to {save_path}: {e}")


def wait_for_games(game_processes, process_info, timeout_seconds, context_label="Set"):
    """Waits for game processes, handles timeouts, and returns summary."""
    completed_normally = 0
    timed_out = 0
    failed_other = 0

    print(f"[Info] Waiting for {len(game_processes)} games in {context_label} to finish (or time out)...")

    for proc in game_processes:
        proc_idx = process_info.get(proc.pid, {}).get("index", "Unknown")
        print(f"[Debug] Waiting for game {proc_idx} (PID: {proc.pid}) with timeout {timeout_seconds}s...") # Debug Print
        try:
            proc.wait(timeout=timeout_seconds)
            # If wait completes without exception
            print(f"[Debug] Game {proc_idx} (PID: {proc.pid}) finished waiting.") # Debug Print
            if proc.returncode == 0:
                print(f"[Debug] Game {proc_idx} completed normally.") # Debug Print
                completed_normally += 1
            else:
                print(f"[Warning] Game {proc_idx} exited with code {proc.returncode}")
                failed_other += 1
        except subprocess.TimeoutExpired:
            print(f"[Warning] Game {proc_idx} (PID: {proc.pid}) exceeded time limit ({timeout_seconds}s). Terminating...") # Debug Print
            try:
                print(f"[Debug] Attempting terminate on PID {proc.pid}...") # Debug Print
                proc.terminate() # Try graceful termination first (SIGTERM)
                proc.wait(timeout=5) # Give it a moment to terminate
                print(f"[Debug] Terminate successful for PID {proc.pid}.") # Debug Print
            except Exception as term_ex:
                print(f"[Debug] Terminate/Wait failed for PID {proc.pid}: {term_ex}. Attempting kill...") # Debug Print
                try:
                     proc.kill() # Force kill (SIGKILL)
                     print(f"[Debug] Kill successful for PID {proc.pid}.") # Debug Print
                except Exception as kill_e:
                     # Process might have already died between terminate and kill
                     print(f"[Error] Failed to kill game {proc_idx} (PID: {proc.pid}): {kill_e}")
            timed_out += 1
        except Exception as e:
             print(f"[Error] Error waiting for game {proc_idx} (PID: {proc.pid}): {e}")
             failed_other += 1

    print(f"[Info] {context_label} Summary: Completed normally: {completed_normally}, Timed out: {timed_out}, Other exit/error: {failed_other}")
    return completed_normally, timed_out, failed_other


def launch_bulk_train(games_per_set, num_sets):
    """Runs multiple sets of game generation and training cycles with time limits."""
    os.makedirs(ITERATIONS_FOLDER, exist_ok=True)

    for set_num in range(num_sets):
        current_set = set_num + 1
        print(f"\n=== Starting Bulk Train Set {current_set} / {num_sets} ===")
        print(f"--- Running {games_per_set} games (Headless, Timeout: {MAX_GAME_DURATION_SECONDS}s) ---")

        game_processes = []
        process_info = {}
        for i in range(games_per_set):
            print(f"[Info] Launching game {i+1}/{games_per_set}...")
            proc = launch_game("bulktrain")
            if proc:
                 game_processes.append(proc)
                 process_info[proc.pid] = {"start_time": time.time(), "index": i+1}
            else:
                 print(f"[Error] Failed to launch game {i+1}, aborting set {current_set}.")
                 for p in game_processes:
                     try: p.terminate()
                     except: pass
                 return

        # --- Wait for processes with Timeout using the helper function ---
        wait_for_games(game_processes, process_info, MAX_GAME_DURATION_SECONDS, f"Set {current_set}")
        # ---

        print(f"\n--- Training Model (Set {current_set}) ---")
        train_model("train")

        print(f"\n--- Saving Checkpoint (Set {current_set}) ---")
        save_model_checkpoint(current_set)

        print(f"\n--- Clearing Logs for Next Set ---")
        clear_game_logs()

        print(f"=== Completed Bulk Train Set {current_set} / {num_sets} ===")

    print("\n[Info] Bulk training procedure completed.")


# --- Main Execution Block ---
if __name__ == "__main__":
    # Default settings
    mode = "play"
    num_games_train = 1
    games_per_set_bulk = 10
    num_sets_bulk = 5

    # --- Argument Parsing ---
    args = sys.argv[1:]
    # (Argument parsing logic remains the same)
    if len(args) > 0:
        mode = args[0].lower()
        if mode not in VALID_MODES: print(f"[Error] Invalid mode '{mode}'. Use one of {VALID_MODES}."); sys.exit(1)
        if mode == "train":
            if len(args) > 1:
                try: num_games_train = int(args[1]); assert num_games_train > 0
                except (ValueError, AssertionError): print(f"[Error] Invalid number of games for train mode: must be positive integer."); sys.exit(1)
        elif mode == "bulktrain":
            if len(args) == 3:
                try:
                    games_per_set_bulk = int(args[1]); assert games_per_set_bulk > 0
                    num_sets_bulk = int(args[2]); assert num_sets_bulk > 0
                except (ValueError, AssertionError): print(f"[Error] Invalid arguments for bulktrain mode: must be positive integers."); sys.exit(1)
            else: print("[Error] Incorrect number of arguments for bulktrain mode.\nUsage: python launch_bot_match.py bulktrain <games_per_set> <num_sets>"); sys.exit(1)
    # --- End Argument Parsing ---

    # --- Print Execution Plan ---
    print(f"[Info] Selected Mode: {mode.upper()}")
    if mode == "train": print(f"[Info] Number of Games: {num_games_train}")
    if mode == "bulktrain": print(f"[Info] Games per Set: {games_per_set_bulk}, Number of Sets: {num_sets_bulk}")
    # --- Explicitly state the timeout value being used ---
    print(f"[Info] Game Timeout Setting: {MAX_GAME_DURATION_SECONDS} seconds")
    # ---

    # --- Initial Log Clearing ---
    if mode == "train" or mode == "bulktrain":
        print("\n--- Initial Log Clearing ---")
        clear_game_logs()
    # ---

    server_process = None
    try:
        # Launch AI server
        server_process = launch_ai_server(mode)
        if not server_process: print("[Error] Failed to launch AI server. Exiting."); sys.exit(1)
        print("[Info] Waiting for AI server to initialize...")
        time.sleep(5)

        # --- Execute Mode-Specific Logic ---
        if mode == "bulktrain":
            launch_bulk_train(games_per_set_bulk, num_sets_bulk)

        elif mode == "train":
            print(f"\n--- Running {num_games_train} Training Game(s) (Headless, Timeout: {MAX_GAME_DURATION_SECONDS}s) ---")
            game_processes = []
            process_info = {}
            for game_num in range(1, num_games_train + 1):
                print(f"[Info] Launching training game {game_num}/{num_games_train}...")
                proc = launch_game(mode)
                if proc:
                    game_processes.append(proc)
                    process_info[proc.pid] = {"start_time": time.time(), "index": game_num}
                else:
                    print(f"[Warning] Failed to launch game {game_num}, continuing...")

            if not game_processes:
                 print("[Error] No games were launched successfully for training.")
            else:
                # --- Wait for processes with Timeout using the helper function ---
                wait_for_games(game_processes, process_info, MAX_GAME_DURATION_SECONDS, "Train Batch")
                # ---

                # Train model after all games complete/timeout
                print("\n--- Training Model ---")
                train_model(mode)

        elif mode == "play": # Play mode (no timeout needed here)
            print("\n--- Starting Play Mode Game (Graphical) ---")
            game_process = launch_game(mode)
            if game_process:
                print("[Info] Waiting for game to finish...")
                try:
                    game_process.wait() # No timeout for play mode
                    print("[Info] Game finished.")
                    print("\n--- Training Model (Fast - Play Mode) ---")
                    train_model(mode)
                    print("\n--- Clearing Logs ---")
                    clear_game_logs()
                except Exception as e:
                     print(f"[Error] Error during game execution or post-play training: {e}")
            else:
                 print("[Error] Failed to launch game in play mode.")
        # --- End Mode-Specific Logic ---

    except Exception as e:
        print(f"\n--- An unexpected error occurred in the main block: {e} ---")
        # Print traceback for debugging
        import traceback
        traceback.print_exc()
    finally:
        # --- Ensure Server Shutdown ---
        shutdown(server_process)
        print("\n[Info] Script execution finished.")