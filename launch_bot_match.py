# launch_bot_match.py

import subprocess
import os
import time
import sys
import shutil
import signal
import traceback
import argparse # Added for argument parsing

#  Constants and Paths (Can be overridden by command-line args)
UNITY_EXECUTABLE = os.path.abspath(os.path.join("client", "CatanLearner.exe"))
AI_SERVER_SCRIPT = os.path.join("server", "catan_ai.py")
TRAINING_SCRIPT = os.path.join("server", "train_from_logs.py")
ITERATIONS_FOLDER = os.path.join("server", "iterations")
MODEL_PATH = os.path.join("server", "model_weights.pth")
VALID_MODES = {"train", "play", "bulktrain"}
MAX_GAME_DURATION_SECONDS = 300

# Global flags for overrides
FORCE_HEADLESS_OVERRIDE = False
FORCE_GRAPHICAL_OVERRIDE = False

# Global Process Tracking
server_process_global = None
game_processes_global = []

# Signal Handler Function
def cleanup_on_interrupt(sig, frame):
    """Handles SIGINT by forcefully terminating known child processes (simplified)."""
    print("\n!!! Signal SIGINT (Ctrl+C): Forcing immediate cleanup...")

    global server_process_global, game_processes_global

    # Terminate Server
    server_terminated = False
    if server_process_global and server_process_global.poll() is None:
        print("--> Terminating AI Server...")
        try:
            server_process_global.kill()
            print("     Server Killed.")
            server_terminated = True
        except Exception as e:
            print(f"     Error killing server (PID: {server_process_global.pid if server_process_global else 'N/A'}): {e}")
    elif server_process_global:
         print("--> AI Server already exited.")
         server_terminated = True
    else:
         print("--> No AI Server process tracked.")
         server_terminated = True

    # Terminate Games
    print("--> Terminating Game Processes...")
    killed_count = 0
    already_exited = 0
    error_count = 0
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
                     killed_count += 1
                 except Exception as kill_e:
                     print(f"     Error killing game PID {pid}: {kill_e}")
                     error_count += 1
             else:
                 already_exited += 1
         except Exception as check_err:
             print(f"     Error checking game process state (PID: {pid}): {check_err}")
             error_count += 1

    print(f"[Cleanup Summary] Server Handled: {server_terminated}, Games Killed: {killed_count}, Games Already Exited: {already_exited}, Errors: {error_count}")
    print("Info: Exiting script after signal cleanup.")
    sys.exit(0)

def clear_game_logs():
    """Moves existing .jsonl logs from SelfPlayLogs to OldLogs with timestamps."""
    log_dir = os.path.abspath(os.path.join("client", "SelfPlayLogs"))
    old_logs_dir = os.path.abspath(os.path.join("client", "OldLogs"))
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(old_logs_dir, exist_ok=True)
    moved_count = 0
    try:
        log_files = os.listdir(log_dir)

        for filename in log_files:
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

        if moved_count > 0: print(f"Info: Moved {moved_count} log file(s) to OldLogs.")
        elif log_files: print("Info: No .jsonl files found in SelfPlayLogs to move.")
        else: print("Info: SelfPlayLogs directory is empty.")

    except Exception as e:
        print(f"[Error] An error occurred during log clearing (Dir: {log_dir}): {e}")

def launch_ai_server(mode):
    """Starts the Python Flask AI server."""
    print("Info: Starting AI Server...")
    print(f"Info: Launching AI Server in {mode.upper()} mode...")


    env = os.environ.copy()
    env["CATAN_TRAIN_MODE"] = "1" if mode == "train" or mode == "bulktrain" else "0"
    try:
        server_process = subprocess.Popen([sys.executable, AI_SERVER_SCRIPT], env=env)
        print(f"Info: AI Server started with PID: {server_process.pid}")
        return server_process
    except FileNotFoundError:
        print(f"[Error] AI Server script not found: {AI_SERVER_SCRIPT}")
        return None
    except Exception as e:
        print(f"[Error] Failed to launch AI Server: {e}")
        return None

def launch_game(mode):
    """Launches the Unity game executable with arguments."""
    headless_flags = []
    bot_mode_flags = []
    global FORCE_HEADLESS_OVERRIDE, FORCE_GRAPHICAL_OVERRIDE # Access overrides

    # Determine bot mode first
    if mode == "train" or mode == "bulktrain":
        bot_mode_flags = ["--bot-vs-bot"]
    elif mode == "play":
        pass # Default is human vs bot in Unity build
    else:
        print(f"[Warning] Unknown mode '{mode}' passed to launch_game.")

    # Determine headless flags based on mode and overrides
    if FORCE_HEADLESS_OVERRIDE:
        headless_flags = ["-batchmode", "-nographics"]
        print("Info: Forcing headless mode via command line argument.")
    elif FORCE_GRAPHICAL_OVERRIDE:
        headless_flags = []
        print("Info: Forcing graphical mode via command line argument.")
    elif mode == "train" or mode == "bulktrain": # Default for train modes
        headless_flags = ["-batchmode", "-nographics"]
    # Else (play mode without overrides): headless_flags remains empty

    command_list = [UNITY_EXECUTABLE] + bot_mode_flags + headless_flags
    print(f"Info: Attempting to execute Unity command: {command_list}")
    try:
        # shell=False is important for process control
        game_process = subprocess.Popen(command_list, shell=False)
        print(f"Info: Launched game process with PID: {game_process.pid}")
        return game_process
    except FileNotFoundError:
         print(f"[Error] Unity executable not found: {UNITY_EXECUTABLE}")
         return None
    except Exception as e:
        print(f"[Error] Failed to launch Unity game process: {e}")
        return None

def train_model(mode):
    """Runs the training script using the logs generated."""
    print(f"Info: Starting training from game logs in {mode.upper()} mode...")
    try:
        result = subprocess.run([sys.executable, TRAINING_SCRIPT, mode], check=False)
        if result.returncode == 0: print("Info: Training completed successfully.\n")
        else: print(f"[Warning] Training script exited with code {result.returncode}.\n")
    except FileNotFoundError:
        print(f"[Error] Training script not found: {TRAINING_SCRIPT}")
    except Exception as e:
        print(f"[Error] An error occurred during training: {e}")

def shutdown(server_proc):
    """Attempts to gracefully terminate the AI server process."""
    if server_proc and server_proc.poll() is None:
        print("Info: Shutting down AI Server...")
        try:
            server_proc.terminate()
            server_proc.wait(timeout=10)
            print("Info: AI Server shut down.")
        except subprocess.TimeoutExpired:
            print("[Warning] AI Server did not terminate gracefully, killing.")
            server_proc.kill()
        except Exception as e:
            print(f"[Error] Error shutting down server: {e}")

def save_model_checkpoint(set_num):
    """Saves a numbered checkpoint copy of the current model weights."""
    if not os.path.exists(MODEL_PATH):
        print(f"[Warning] Main model file {MODEL_PATH} not found. Cannot create checkpoint.")
        return
    os.makedirs(ITERATIONS_FOLDER, exist_ok=True)
    save_name = f"settlerbot_{set_num}.pth"
    save_path = os.path.join(ITERATIONS_FOLDER, save_name)
    try:
        shutil.copy2(MODEL_PATH, save_path)
        print(f"Info: Saved model checkpoint to {save_path}")
    except Exception as e:
        print(f"[Error] Failed to save model checkpoint to {save_path}: {e}")

def wait_for_games(game_processes, process_info, timeout_seconds, context_label="Set"):
    """Waits for game processes using polling, handles timeout (simplified)."""
    if not game_processes:
        print(f"Info: {context_label} Summary: No games to wait for.")
        return 0, 0, 0

    start_time = time.time()
    end_time = start_time + timeout_seconds
    running_procs = {proc: process_info.get(proc.pid, {"index": "Unknown", "pid": proc.pid})
                     for proc in game_processes if proc and proc.poll() is None}

    completed_normally = 0
    timed_out = 0
    failed_other = 0
    processed_pids = set()

    print(f"Info: Waiting for {len(running_procs)} games in {context_label} (Timeout: {timeout_seconds}s)...")

    while running_procs and time.time() < end_time:
        for proc in list(running_procs.keys()):
            return_code = proc.poll()
            if return_code is not None:
                status_info = running_procs[proc]
                pid = status_info.get("pid", "N/A")
                idx = status_info.get("index", "Unknown")
                processed_pids.add(pid)

                if return_code == 0:
                    completed_normally += 1
                else:
                    print(f"[Warning] Game {idx} (PID: {pid}) exited with code {return_code}.")
                    failed_other += 1
                del running_procs[proc]
        time.sleep(0.1)

    if running_procs:
        print(f"[Warning] Global timeout reached ({timeout_seconds}s). Terminating {len(running_procs)} remaining game(s)...")
        for proc in running_procs:
            status_info = running_procs[proc]
            pid = status_info.get("pid", "N/A")
            idx = status_info.get("index", "Unknown")
            processed_pids.add(pid)
            timed_out += 1
            print(f"  -> Terminating timed-out game {idx} (PID: {pid})...")
            try:
                proc.kill()
            except Exception as e:
                print(f"     Error killing timed-out game {idx} (PID: {pid}): {e}")

    final_check_completed = 0
    final_check_failed = 0
    for proc in game_processes:
        if proc and proc.pid not in processed_pids:
             pid = proc.pid
             idx = process_info.get(pid, {}).get("index", "Unknown")
             if proc.poll() is not None:
                  if proc.returncode == 0:
                       final_check_completed += 1
                  else:
                       print(f"[Warning] Game {idx} (PID: {pid}) finished outside main wait loop (Code: {proc.returncode}).")
                       final_check_failed += 1
             else:
                  print(f"[Error] Game {idx} (PID: {pid}) state unclear after wait finished & not timed out.")
                  final_check_failed += 1

    total_completed = completed_normally + final_check_completed
    total_failed = failed_other + final_check_failed

    print(f"Info: {context_label} Summary: Completed normally: {total_completed}, Timed out: {timed_out}, Other exit/error: {total_failed}")
    return total_completed, timed_out, total_failed

def launch_bulk_train(games_per_set, num_sets, outer_game_processes_list):
    """Runs multiple sets of game generation and training cycles with time limits."""
    os.makedirs(ITERATIONS_FOLDER, exist_ok=True)

    for set_num in range(num_sets):
        current_set = set_num + 1
        print(f"\n=== Starting Bulk Train Set {current_set} / {num_sets} ===")
        print(f" Running {games_per_set} games (Timeout: {MAX_GAME_DURATION_SECONDS}s) ") # Removed Headless mention, handled by launch_game

        current_set_processes = []
        process_info = {}

        for i in range(games_per_set):
            proc = launch_game("bulktrain")
            if proc:
                 outer_game_processes_list.append(proc)
                 current_set_processes.append(proc)
                 process_info[proc.pid] = {"start_time": time.time(), "index": i+1}
            else:
                 print(f"[Error] Failed to launch game {i+1}, aborting set {current_set}.")
                 for p in current_set_processes:
                     try: p.terminate()
                     except: pass
                 return

        wait_for_games(current_set_processes, process_info, MAX_GAME_DURATION_SECONDS, f"Set {current_set}")

        print(f"\n Training Model (Set {current_set}) ")
        train_model("train")

        print(f"\n Saving Checkpoint (Set {current_set}) ")
        save_model_checkpoint(current_set)

        print(f"\n Clearing Logs for Next Set ")
        clear_game_logs()

        temp_outer_list = list(outer_game_processes_list)
        for p in current_set_processes:
            if p in temp_outer_list and p.poll() is not None:
                try: outer_game_processes_list.remove(p)
                except ValueError: pass

        print(f"=== Completed Bulk Train Set {current_set} / {num_sets} ===")

    print("\nInfo: Bulk training procedure completed.")


# https://docs.python.org/3/howto/argparse.html
def parse_args():
    """Parses command line arguments and overrides global constants if provided."""
    global MAX_GAME_DURATION_SECONDS, UNITY_EXECUTABLE, AI_SERVER_SCRIPT
    global TRAINING_SCRIPT, MODEL_PATH, FORCE_HEADLESS_OVERRIDE, FORCE_GRAPHICAL_OVERRIDE

    parser = argparse.ArgumentParser(description="Launch Catan AI Bot Matches.", add_help=False) # Defer help

    # Optional arguments group
    optional = parser.add_argument_group('Optional Overrides')
    optional.add_argument('--timeout', type=int, metavar='SECONDS',
                        help=f'Override max game duration (default: {MAX_GAME_DURATION_SECONDS}s)')
    
    display_group = optional.add_mutually_exclusive_group()

    display_group.add_argument('--force-headless', action='store_true',
                        help='Force Unity to run in headless mode (-batchmode -nographics)')
    
    display_group.add_argument('--force-graphical', action='store_true',
                        help='Force Unity to run in graphical mode (no headless flags)')
    
    optional.add_argument('--unity-exe', type=str, metavar='PATH',
                        help=f'Override path to Unity executable (default: {UNITY_EXECUTABLE})')
    
    optional.add_argument('--server-script', type=str, metavar='PATH',
                        help=f'Override path to AI server script (default: {AI_SERVER_SCRIPT})')
    
    optional.add_argument('--train-script', type=str, metavar='PATH',
                        help=f'Override path to training script (default: {TRAINING_SCRIPT})')
    
    optional.add_argument('--model-weights', type=str, metavar='PATH',
                        help=f'Override path to model weights file (default: {MODEL_PATH})')
    
    optional.add_argument('-h', '--help', action='store_true', help='Show this help message and exit')


    # Use parse_known_args to separate optional flags from positional mode args
    args, remaining_args = parser.parse_known_args()

    if args.help:
         print("Usage: python launch_bot_match.py [mode] [mode_args...] [options]\n")
         print("Modes:")
         print("  play                     Run Human vs Bot (graphical default)")
         print("  train <n_games>          Run N Bot vs Bot games (headless default), then train")
         print("  bulktrain <games> <sets> Run games/set for num_sets (headless default), train & checkpoint each set\n")
         parser.print_help()
         sys.exit(0)


    # Apply overrides from optional arguments
    if args.timeout is not None:
        MAX_GAME_DURATION_SECONDS = args.timeout
        print(f"[Override] Max game duration set to: {MAX_GAME_DURATION_SECONDS}s")
    if args.force_headless:
        FORCE_HEADLESS_OVERRIDE = True
    if args.force_graphical:
        FORCE_GRAPHICAL_OVERRIDE = True
    if args.unity_exe:
        UNITY_EXECUTABLE = os.path.abspath(args.unity_exe)
        print(f"[Override] Unity executable path set to: {UNITY_EXECUTABLE}")
    if args.server_script:
        AI_SERVER_SCRIPT = os.path.abspath(args.server_script)
        print(f"[Override] AI server script path set to: {AI_SERVER_SCRIPT}")
    if args.train_script:
        TRAINING_SCRIPT = os.path.abspath(args.train_script)
        print(f"[Override] Training script path set to: {TRAINING_SCRIPT}")
    if args.model_weights:
        MODEL_PATH = os.path.abspath(args.model_weights)
        print(f"[Override] Model weights path set to: {MODEL_PATH}")

    return remaining_args # Return positional arguments for mode processing

# Main Execution Block
if __name__ == "__main__":

    remaining_args = parse_args()

    # Default settings
    mode = "play"
    num_games_train = 1
    games_per_set_bulk = 10
    num_sets_bulk = 5

    if len(remaining_args) > 0:
        mode = remaining_args[0].lower()
        if mode not in VALID_MODES:
            print(f"[Error] Invalid mode '{mode}'. Use one of {VALID_MODES}.")
            sys.exit(1)
        if mode == "train":
            if len(remaining_args) > 1:
                try: num_games_train = int(remaining_args[1]); assert num_games_train > 0
                except (ValueError, AssertionError): print(f"[Error] Invalid number of games for train mode: must be positive integer."); sys.exit(1)

            else: # Require number of games for train mode
                print(f"[Error] Missing number of games for train mode.")
                print("Usage: python launch_bot_match.py train <n_games> [options]")
                sys.exit(1)

        elif mode == "bulktrain":
            if len(remaining_args) == 3:
                try: games_per_set_bulk = int(remaining_args[1]); assert games_per_set_bulk > 0; num_sets_bulk = int(remaining_args[2]); assert num_sets_bulk > 0
                except (ValueError, AssertionError): print(f"[Error] Invalid arguments for bulktrain mode: must be positive integers."); sys.exit(1)

            else:
                print("[Error] Incorrect number of arguments for bulktrain mode.")
                print("Usage: python launch_bot_match.py bulktrain <games_per_set> <num_sets> [options]")
                sys.exit(1)

        elif mode == "play" and len(remaining_args) > 1:
             print(f"[Warning] Extra arguments provided for 'play' mode: {remaining_args[1:]}. Ignored.")

    # Print Execution Plan (Reflects overrides)
    print(f"\nSelected Mode: {mode.upper()}")
    if mode == "train": print(f"Number of Games: {num_games_train}")
    if mode == "bulktrain": print(f"Games per Set: {games_per_set_bulk}, Number of Sets: {num_sets_bulk}")
    print(f"Game Timeout Setting: {MAX_GAME_DURATION_SECONDS} seconds")

    # Print override info if applied
    if FORCE_HEADLESS_OVERRIDE: print("Headless Mode: Forced ON")
    elif FORCE_GRAPHICAL_OVERRIDE: print("Headless Mode: Forced OFF")

    signal.signal(signal.SIGINT, cleanup_on_interrupt)

    if mode == "train" or mode == "bulktrain":
        print("\n Initial Log Clearing")
        clear_game_logs()

    game_processes_global = []

    try:
        server_process_global = launch_ai_server(mode)
        if not server_process_global:
            sys.exit(1)
        print("Info: Waiting for AI server to initialize...")
        time.sleep(5)

        if mode == "bulktrain":
            launch_bulk_train(games_per_set_bulk, num_sets_bulk, game_processes_global)

        elif mode == "train":
            print(f"\n Running {num_games_train} Training Game(s) (Timeout: {MAX_GAME_DURATION_SECONDS}s)")
            process_info = {}
            current_train_processes = []
            for game_num in range(1, num_games_train + 1):
                proc = launch_game(mode)
                if proc:
                    game_processes_global.append(proc)
                    current_train_processes.append(proc)
                    process_info[proc.pid] = {"start_time": time.time(), "index": game_num}
                else:
                    print(f"[Warning] Failed to launch game {game_num}, continuing...")

            if not current_train_processes:
                 print("[Error] No games were launched successfully for training.")
            else:
                wait_for_games(current_train_processes, process_info, MAX_GAME_DURATION_SECONDS, "Train Batch")
                print("\n Training Model")
                train_model(mode)

                temp_outer_list = list(game_processes_global)
                for p in current_train_processes:
                    if p in temp_outer_list and p.poll() is not None:
                        try: game_processes_global.remove(p)
                        except ValueError: pass

        elif mode == "play":
            print("\n Starting Play Mode Game")
            game_process = launch_game(mode)
            if game_process:
                 game_processes_global.append(game_process)
                 print("Info: Waiting for game to finish...")
                 try:
                    game_process.wait()
                    print("Info: Game finished.")
                    print("\n Training Model (Fast - Play Mode)")
                    train_model(mode)
                    print("\n Clearing Logs")
                    clear_game_logs()

                    if game_process in game_processes_global:
                         try: game_processes_global.remove(game_process)
                         except ValueError: pass
                 except Exception as e:
                     print(f"[Error] Error during game execution or post-play steps: {e}")
            else:
                 print("[Error] Failed to launch game in play mode.")

        # Normal Exit Cleanup
        print("\nInfo: Script completed normally. Performing final check/cleanup...")
        if server_process_global and server_process_global.poll() is None:
             shutdown(server_process_global)

        final_cleanup_count = 0
        processes_to_check = list(game_processes_global)
        for proc in processes_to_check:
             if proc and proc.poll() is None:
                  print(f"  -> Cleaning up leftover game PID: {proc.pid}")
                  try: proc.kill()
                  except Exception as final_kill_e:
                      print(f"     Error killing leftover game PID {proc.pid}: {final_kill_e}")
                  final_cleanup_count += 1
        if final_cleanup_count > 0: print(f"  Cleaned up {final_cleanup_count} leftover game processes.")

    except Exception as e:
        print(f"\n An unexpected error occurred in the main block: {e} ")
        traceback.print_exc()

    finally:
        print("\nInfo: Script execution finished.")