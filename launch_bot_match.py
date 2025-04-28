# launch_bot_match.py

import subprocess
import os
import time
import sys
import shutil
import signal

#  Constants and Paths 
UNITY_EXECUTABLE = os.path.abspath(os.path.join("client", "CatanLearner.exe"))
AI_SERVER_SCRIPT = os.path.join("server", "catan_ai.py")
TRAINING_SCRIPT = os.path.join("server", "train_from_logs.py")
ITERATIONS_FOLDER = os.path.join("server", "iterations")
MODEL_PATH = os.path.join("server", "model_weights.pth")
VALID_MODES = {"train", "play", "bulktrain"}
#  Timeout Constant - SET THIS AS NEEDED 
MAX_GAME_DURATION_SECONDS = 15 # Set to 3 minutes (180 seconds)
#  End Constants 


# Global Process Tracking
server_process_global = None
game_processes_global = []

# Signal Handler Function
def cleanup_on_interrupt(sig, frame):
    """
    Handles SIGINT by forcefully terminating known child processes.
    """
    print("\n[!] Signal SIGINT (Ctrl+C) received. Forcing immediate cleanup...")

    global server_process_global, game_processes_global

    # Terminate Server
    server_terminated = False
    if server_process_global and server_process_global.poll() is None:
        print("  -> Terminating AI Server...")
        try:
            # Use kill directly for speed on interrupt
            server_process_global.kill()
            # Optional short wait
            try: server_process_global.wait(timeout=0.5)
            except Exception: pass
            print("     Server Killed.")
            server_terminated = True
        except Exception as e:
            print(f"     Error killing server: {e}")
    elif server_process_global:
         print("  -> AI Server already exited.")
         server_terminated = True # Consider it handled if already exited
    else:
         print("  -> No AI Server process tracked.")
         server_terminated = True # No server to terminate

    # Terminate Games
    print("  -> Terminating Game Processes...")
    killed_count = 0
    already_exited = 0
    error_count = 0
    # Iterate over a copy in case list is modified elsewhere (though unlikely in handler)
    processes_to_kill = list(game_processes_global)

    for proc in processes_to_kill:
         if not proc: continue
         pid = "Unknown"
         try: pid = proc.pid
         except Exception: pass

         try:
             if proc.poll() is None:
                 print(f"     Killing game PID: {pid}")
                 try:
                     proc.kill()
                     # Optional short wait after kill
                     try: proc.wait(timeout=0.5)
                     except Exception: pass
                     killed_count += 1
                 except Exception as kill_e:
                     # Check again - maybe it died just now?
                     if proc.poll() is None:
                         print(f"     Error killing game PID {pid}: {kill_e}")
                         error_count += 1
                     else:
                         already_exited += 1
             else:
                 already_exited += 1
         except Exception as poll_err:
             print(f"     Error checking game process (PID: {pid}): {poll_err}")
             error_count += 1

    print(f"[Cleanup Summary] Server Handled: {server_terminated}, Games Killed: {killed_count}, Games Already Exited: {already_exited}, Errors: {error_count}")

    # Exit the script immediately after handling the interrupt
    print("[Info] Exiting script after signal cleanup.")
    sys.exit(0)

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
        bot_mode_flags = ["--bot-vs-bot"]
    elif mode == "play":
        # bot_mode_flags = ["--human-vs-bot"]
        pass
    else:
        print(f"[Warning] Unknown mode '{mode}' passed to launch_game.")

    #  Construct command list 
    command_list = [UNITY_EXECUTABLE] # Start with the executable path
    command_list.extend(bot_mode_flags)
    command_list.extend(headless_flags)

    print(f"[Info] Attempting to execute Unity command list: {command_list}")
    try:
        #  Use shell=False (default) and pass the list 
        # This makes the unity process a child of the current process group
        # and allows for better control over process termination.
        game_process = subprocess.Popen(command_list, shell=False)

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
    """
    Waits for game processes using polling, handling a global timeout concurrently.
    Returns summary statistics.
    """
    if not game_processes:
        print(f"[Info] {context_label} Summary: No games to wait for.")
        return 0, 0, 0

    start_time = time.time()
    end_time = start_time + timeout_seconds

    # Keep track of processes still running
    # Use a dictionary {proc_object: status_info} for easier updates
    # Status info could be pid, index, or initial process_info entry
    running_procs = {proc: process_info.get(proc.pid, {"index": "Unknown", "pid": proc.pid})
                     for proc in game_processes if proc and proc.poll() is None}

    completed_normally = 0
    timed_out = 0
    failed_other = 0
    processed_pids = set() # Track PIDs already logged as finished/failed

    print(f"[Info] Waiting for {len(running_procs)} games in {context_label} to finish (Global Timeout: {timeout_seconds}s)...")

    while running_procs and time.time() < end_time:
        # Check each running process without blocking for long
        # Iterate over a copy of keys since we might modify the dict
        for proc in list(running_procs.keys()):
            if proc.poll() is not None: # Process has finished
                status_info = running_procs[proc]
                pid = status_info.get("pid", "N/A")
                idx = status_info.get("index", "Unknown")
                processed_pids.add(pid)

                if proc.returncode == 0:
                    print(f"[Debug] Game {idx} (PID: {pid}) completed normally.")
                    completed_normally += 1
                else:
                    print(f"[Warning] Game {idx} (PID: {pid}) exited with code {proc.returncode}.")
                    failed_other += 1

                # Remove from running list
                del running_procs[proc]

        # Sleep briefly to avoid busy-waiting and consuming 100% CPU
        time.sleep(0.1) # Check roughly 10 times per second

    #  Timeout Check 
    # After the loop, any process remaining in running_procs has timed out
    if running_procs:
        print(f"[Warning] Global timeout reached ({timeout_seconds}s). Terminating {len(running_procs)} remaining game(s)...")
        for proc in running_procs:
            status_info = running_procs[proc]
            pid = status_info.get("pid", "N/A")
            idx = status_info.get("index", "Unknown")
            processed_pids.add(pid) # Mark as processed (timed out)
            timed_out += 1

            print(f"  -> Terminating timed-out game {idx} (PID: {pid})...")
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=1) # Short wait for terminate
                except subprocess.TimeoutExpired:
                    print(f"     Terminate failed for PID {pid}. Killing...")
                    proc.kill()
                    try: proc.wait(timeout=0.5) # Short wait after kill
                    except Exception: pass
            except Exception as e:
                print(f"     Error terminating/killing game {idx} (PID: {pid}): {e}")

    #  Final Check & Logging 
    # Check original list for any processes missed or already finished before polling started
    for proc in game_processes:
        if proc and proc.pid not in processed_pids:
             pid = proc.pid
             idx = process_info.get(pid, {}).get("index", "Unknown")
             if proc.poll() is not None: # Finished before loop or timeout check
                 if proc.returncode == 0:
                    # Should have been caught above, but log just in case
                    print(f"[Debug] Game {idx} (PID: {pid}) finished outside main check (Code: 0).")
                    completed_normally += 1
                 else:
                    print(f"[Warning] Game {idx} (PID: {pid}) finished outside main check (Code: {proc.returncode}).")
                    failed_other += 1
             else:
                  # This shouldn't happen if logic is correct, but log if it does
                  print(f"[Error] Game {idx} (PID: {pid}) state unclear after waiting.")
                  failed_other += 1


    print(f"[Info] {context_label} Summary: Completed normally: {completed_normally}, Timed out: {timed_out}, Other exit/error: {failed_other}")
    return completed_normally, timed_out, failed_other


def launch_bulk_train(games_per_set, num_sets, outer_game_processes_list):
    """Runs multiple sets of game generation and training cycles with time limits."""
    os.makedirs(ITERATIONS_FOLDER, exist_ok=True)

    for set_num in range(num_sets):
        current_set = set_num + 1
        print(f"\n=== Starting Bulk Train Set {current_set} / {num_sets} ===")
        print(f" Running {games_per_set} games (Headless, Timeout: {MAX_GAME_DURATION_SECONDS}s) ")

        # Keep track of processes specifically for *this* set for waiting
        current_set_processes = []
        process_info = {} # Still needed for wait_for_games context

        for i in range(games_per_set):
            print(f"[Info] Launching game {i+1}/{games_per_set}...")
            proc = launch_game("bulktrain") # Mode ensures bot-vs-bot
            if proc:
                 # Append to the list passed from the main scope (for Ctrl+C cleanup)
                 outer_game_processes_list.append(proc)
                 # Also append to the local list for this set's wait_for_games call
                 current_set_processes.append(proc)
                 process_info[proc.pid] = {"start_time": time.time(), "index": i+1}
            else:
                 print(f"[Error] Failed to launch game {i+1}, aborting set {current_set}.")
                 # Attempt cleanup of already launched processes *in this set* before returning
                 for p in current_set_processes:
                     try: p.terminate()
                     except: pass # Ignore errors during this specific cleanup
                 # Note: Processes added to outer_game_processes_list will be caught by final cleanup
                 return # Exit the function

        #  Wait for processes *of the current set* using the helper function 
        wait_for_games(current_set_processes, process_info, MAX_GAME_DURATION_SECONDS, f"Set {current_set}")

        print(f"\n Training Model (Set {current_set}) ")
        train_model("train") # Use 'train' mode parameters for training script

        print(f"\n Saving Checkpoint (Set {current_set}) ")
        save_model_checkpoint(current_set)

        print(f"\n Clearing Logs for Next Set ")
        clear_game_logs()

        # Cleanup: Remove completed processes from the outer list just in case
        for p in current_set_processes:
            if p in outer_game_processes_list and p.poll() is not None:
                outer_game_processes_list.remove(p)

        print(f"=== Completed Bulk Train Set {current_set} / {num_sets} ===")

    print("\n[Info] Bulk training procedure completed.")


# Main Execution Block
if __name__ == "__main__":
    # Default settings
    mode = "play"
    num_games_train = 1
    games_per_set_bulk = 10
    num_sets_bulk = 5

    # Argument Parsing
    args = sys.argv[1:]
    if len(args) > 0:
        mode = args[0].lower()
        if mode not in VALID_MODES:
            print(f"[Error] Invalid mode '{mode}'. Use one of {VALID_MODES}.")
            sys.exit(1)
        if mode == "train":
            if len(args) > 1:
                try:
                    num_games_train = int(args[1])
                    assert num_games_train > 0
                except (ValueError, AssertionError):
                    print(f"[Error] Invalid number of games for train mode: must be positive integer.")
                    sys.exit(1)
        elif mode == "bulktrain":
            if len(args) == 3:
                try:
                    games_per_set_bulk = int(args[1])
                    assert games_per_set_bulk > 0
                    num_sets_bulk = int(args[2])
                    assert num_sets_bulk > 0
                except (ValueError, AssertionError):
                    print(f"[Error] Invalid arguments for bulktrain mode: must be positive integers.")
                    sys.exit(1)
            else:
                print("[Error] Incorrect number of arguments for bulktrain mode.")
                print("Usage: python launch_bot_match.py bulktrain <games_per_set> <num_sets>")
                sys.exit(1)
    # End Argument Parsing

    # Print Execution Plan
    print(f"[Info] Selected Mode: {mode.upper()}")
    if mode == "train": print(f"[Info] Number of Games: {num_games_train}")
    if mode == "bulktrain": print(f"[Info] Games per Set: {games_per_set_bulk}, Number of Sets: {num_sets_bulk}")
    print(f"[Info] Game Timeout Setting: {MAX_GAME_DURATION_SECONDS} seconds")

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, cleanup_on_interrupt)

    # Initial Log Clearing
    if mode == "train" or mode == "bulktrain":
        print("\n Initial Log Clearing")
        clear_game_logs()


    game_processes_global = [] # Ensure list is empty at start

    try:
        # Launch AI server
        server_process_global = launch_ai_server(mode)
        if not server_process_global:
            print("[Error] Failed to launch AI server. Exiting.")
            sys.exit(1)
        print("[Info] Waiting for AI server to initialize...")
        time.sleep(5) # Allow server time to start up

        # Execute Mode-Specific Logic
        if mode == "bulktrain":
            # Pass the global list for process tracking
            launch_bulk_train(games_per_set_bulk, num_sets_bulk, game_processes_global)

        elif mode == "train":
            print(f"\n Running {num_games_train} Training Game(s) (Timeout: {MAX_GAME_DURATION_SECONDS}s)")
            process_info = {}
            current_train_processes = [] # Track processes for this specific train run
            for game_num in range(1, num_games_train + 1):
                print(f"[Info] Launching training game {game_num}/{num_games_train}...")
                proc = launch_game(mode)
                if proc:
                    game_processes_global.append(proc) # Add to global list
                    current_train_processes.append(proc) # Add to local list for wait
                    process_info[proc.pid] = {"start_time": time.time(), "index": game_num}
                else:
                    print(f"[Warning] Failed to launch game {game_num}, continuing...")

            if not current_train_processes:
                 print("[Error] No games were launched successfully for training.")
            else:
                # Wait for the processes launched in this batch
                wait_for_games(current_train_processes, process_info, MAX_GAME_DURATION_SECONDS, "Train Batch")
                print("\n Training Model")
                train_model(mode)

                for p in current_train_processes:
                     if p in game_processes_global and p.poll() is not None:
                          try: game_processes_global.remove(p)
                          except ValueError: pass

        elif mode == "play":
            print("\n Starting Play Mode Game (Graphical)")
            game_process = launch_game(mode)
            if game_process:
                 game_processes_global.append(game_process) # Add to global list
                 print("[Info] Waiting for game to finish...")
                 try:
                    game_process.wait() # Wait indefinitely for player interaction
                    print("[Info] Game finished.")
                    print("\n Training Model (Fast - Play Mode)")
                    train_model(mode)
                    print("\n Clearing Logs")
                    clear_game_logs()
                    # Remove finished process from global list
                    if game_process in game_processes_global:
                         try: game_processes_global.remove(game_process)
                         except ValueError: pass
                 except Exception as e:
                     print(f"[Error] Error during game execution or post-play steps: {e}")
            else:
                 print("[Error] Failed to launch game in play mode.")
        # End Mode-Specific Logic

        # Normal Exit Cleanup 
        # This code runs only if the script finishes without interrupt
        print("\n[Info] Script completed normally. Performing final check/cleanup...")
        if server_process_global and server_process_global.poll() is None:
             shutdown(server_process_global) # Attempt graceful shutdown first
        # Check for any game processes that might still be running (shouldn't happen often)
        final_cleanup_count = 0
        processes_to_check = list(game_processes_global) # Iterate copy
        for proc in processes_to_check:
             if proc and proc.poll() is None:
                  print(f"  -> Cleaning up leftover game PID: {proc.pid}")
                  try: proc.kill()
                  except: pass
                  final_cleanup_count += 1
        if final_cleanup_count > 0: print(f"  Cleaned up {final_cleanup_count} leftover game processes.")


    except Exception as e:
        # Catch other exceptions (KeyboardInterrupt now handled by signal)
        if isinstance(e, KeyboardInterrupt):
             # This might still happen if signal registration failed or during handler itself
             print("\n[!] KeyboardInterrupt caught unexpectedly in main block.")
        else:
             print(f"\n An unexpected error occurred in the main block: {e} ")
             import traceback
             traceback.print_exc()

    finally:
        # This block now mainly confirms script exit.
        # Process cleanup is handled by the signal handler or normal exit logic.
        print("\n[Info] Script execution finished.")