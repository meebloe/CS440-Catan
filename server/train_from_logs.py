# server/train_from_logs.py

import torch
import torch.nn as nn
import torch.optim as optim
import json
import os
import random
import sys
from tqdm import tqdm
import logging
import numpy as np

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import from other modules
try:
    if __package__:
        from .model import CatanSimpleMLP
        from .game_state_encoder import vectorize_state, TOTAL_VECTOR_SIZE
        from .action_mapping import get_action_index, TOTAL_ACTIONS
    else:
        from model import CatanSimpleMLP
        from game_state_encoder import vectorize_state, TOTAL_VECTOR_SIZE
        from action_mapping import get_action_index, TOTAL_ACTIONS
except ImportError as e:
     logging.error(f"Import Error: {e}. Make sure running from correct directory or package installed.")
     sys.exit(1)

#  Paths 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "..", "client", "SelfPlayLogs")
WEIGHTS_PATH = os.path.join(SCRIPT_DIR, "model_weights.pth")

#  Hyperparameters 
NORMAL_LR = 0.001
FAST_LR = 0.01
EPOCHS = 5
BATCH_SIZE = 256

#  Reward Shaping Parameters
BASE_WIN_BONUS = 10.0
TARGET_TURNS = 120
MAX_TURNS = 400

#  Play Mode Boost 
# How many times to duplicate samples from Human vs Bot games
PLAY_MODE_DUPLICATION_FACTOR = 20 # Increased for play mode to boost training from human games

# 

#  Updated load_training_data with duplication_factor 
def load_training_data(log_dir, duplication_factor=1):
    """
    Loads training data from .jsonl logs, applying reward shaping and sample duplication.

    Args:
        log_dir (str): Path to the directory containing log files.
        duplication_factor (int): How many times to repeat each sample (turn).
                                   Defaults to 1. Use >1 for play mode boost.
    """
    states, actions, rewards = [], [], []
    logging.info(f"Attempting to load logs from: {log_dir}")
    if duplication_factor > 1:
        logging.info(f"Applying Sample Duplication Factor: {duplication_factor}")
    logging.info(f"Reward shaping: BaseWinBonus={BASE_WIN_BONUS}, TargetTurns={TARGET_TURNS}, MaxTurns={MAX_TURNS}")

    # ... (rest of the initial checks and file listing remain the same) ...
    if not os.path.exists(log_dir) or not os.path.isdir(log_dir): # Check added here
        logging.error(f"Log directory {log_dir} does not exist!")
        return states, actions, rewards

    log_files = [f for f in os.listdir(log_dir) if f.endswith(".jsonl")]
    if not log_files: # Check added here
        logging.warning(f"No .jsonl files found in {log_dir}.")
        return states, actions, rewards
    # 

    logging.info(f"Found {len(log_files)} log files.")
    processed_games = 0
    processed_turns = 0
    invalid_data_points = 0
    games_with_issues = 0

    for file_name in log_files:
        file_path = os.path.join(log_dir, file_name)
        game_processed_successfully = True
        try:
            with open(file_path, "r") as f:
                line = f.readline()
                if not line.strip():
                    logging.warning(f"Skipping empty log file: {file_name}")
                    games_with_issues += 1
                    continue
                game_record = json.loads(line.strip())

            winner_index = game_record.get("winnerPlayerIndex", -1)
            turns = game_record.get("turns", [])
            num_turns = len(turns)

            if not turns:
                logging.warning(f"Skipping game with no turns in {file_name}")
                games_with_issues += 1
                continue

            # Calculate Speed Multiplier
            speed_multiplier = 0.0
            if winner_index != -1:
                if num_turns <= TARGET_TURNS: speed_multiplier = 1.0
                elif num_turns > MAX_TURNS: speed_multiplier = 0.0
                else: speed_multiplier = 1.0 - ((num_turns - TARGET_TURNS) / float(MAX_TURNS - TARGET_TURNS))
                logging.debug(f"Game {file_name}: Winner {winner_index}, Turns {num_turns}, SpeedMultiplier {speed_multiplier:.3f}")

            # Find Last Winning Turn Index
            last_winning_turn_index = -1
            if winner_index != -1:
                for idx in range(num_turns - 1, -1, -1):
                    if turns[idx].get("state", {}).get("currentPlayerIndex") == winner_index:
                        last_winning_turn_index = idx
                        break

            # Process each turn
            for idx, turn in enumerate(turns):
                try:
                    state = turn.get("state")
                    action = turn.get("action")
                    original_reward = turn.get("reward")

                    if state is None or action is None or original_reward is None:
                        invalid_data_points += 1
                        continue

                    state_vector = vectorize_state(state)
                    if state_vector is None:
                        invalid_data_points += 1
                        continue

                    action_idx = get_action_index(action)
                    if action_idx is None:
                        invalid_data_points += 1
                        continue

                    final_reward = float(original_reward)
                    if idx == last_winning_turn_index:
                        applied_bonus = BASE_WIN_BONUS * speed_multiplier
                        final_reward += applied_bonus
                        if applied_bonus > 0: logging.debug(f"  Applied speed bonus {applied_bonus:.2f} to turn {idx} (Final reward: {final_reward:.2f})")

                    #  Apply Duplication 
                    for _ in range(duplication_factor):
                        states.append(state_vector)
                        actions.append(action_idx)
                        rewards.append(final_reward)
                    # 
                    processed_turns += 1 # Count original turns processed

                except Exception as turn_err:
                    logging.warning(f"Error processing turn {idx} in {file_name}: {turn_err}")
                    invalid_data_points += 1
                    game_processed_successfully = False
                    continue # Continue processing other turns if possible

            if game_processed_successfully:
                processed_games += 1

        except json.JSONDecodeError:
            logging.warning(f"Skipping invalid JSON in file: {file_name}")
            games_with_issues += 1
        except Exception as file_err:
            logging.error(f"Error processing file {file_name}: {file_err}")
            games_with_issues += 1

    logging.info(f"Finished loading logs. Processed {processed_games} games successfully.")
    if games_with_issues > 0: logging.warning(f"Skipped or encountered issues processing {games_with_issues} game files.")
    # Log the total number of samples *after* duplication
    final_sample_count = len(states)
    logging.info(f"Total original turns processed: {processed_turns}. Invalid/skipped data points: {invalid_data_points}.")
    logging.info(f"Total training samples loaded (after duplication): {final_sample_count}.")
    if final_sample_count == 0: logging.error("No valid training data loaded!")
    return states, actions, rewards


def train(mode="train"):
    logging.info(f"Starting training in '{mode}' mode.")

    #  Determine Duplication Factor based on mode 
    effective_duplication_factor = 1
    if mode == "play":
        effective_duplication_factor = PLAY_MODE_DUPLICATION_FACTOR
        logging.info(f"Play mode detected. Applying duplication factor: {effective_duplication_factor}")
    # 

    if not os.path.exists(LOG_DIR) or not os.path.isdir(LOG_DIR):
        logging.error(f"Log directory {LOG_DIR} does not exist. Nothing to train.")
        return

    # Determine Device
    if torch.cuda.is_available(): device = torch.device("cuda"); logging.info("Using GPU.")
    else: device = torch.device("cpu"); logging.info("Using CPU.")

    #  Load Data with potential duplication 
    states, actions, rewards = load_training_data(LOG_DIR, duplication_factor=effective_duplication_factor)
    # 
    if not states:
        logging.error("No valid training data loaded. Exiting.")
        return
    num_samples = len(states) # This is now the potentially duplicated count

    # Adjust batch size if fewer samples than BATCH_SIZE
    if num_samples < BATCH_SIZE:
        logging.warning(f"Total samples ({num_samples}) < Batch size ({BATCH_SIZE}). Reducing batch size.")
        effective_batch_size = max(1, num_samples)
    else:
        effective_batch_size = BATCH_SIZE
    logging.info(f"Using Effective Batch Size: {effective_batch_size}")

    # Model Setup
    model = CatanSimpleMLP(input_size=TOTAL_VECTOR_SIZE, output_size=TOTAL_ACTIONS)
    if os.path.exists(WEIGHTS_PATH):
        try: model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device)); logging.info(f"Loaded weights onto {device}.")
        except Exception as e: logging.error(f"Error loading weights: {e}. Training from scratch.");
    else: logging.info(f"No existing weights found. Training from scratch.")
    model.to(device)

    # Optimizer and Loss
    lr = FAST_LR if mode == "play" else NORMAL_LR
    logging.info(f"Using learning rate: {lr}")
    optimizer = optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    #  Training Loop 
    model.train()
    dataset = list(zip(states, actions, rewards))
    for epoch in range(EPOCHS):
        random.shuffle(dataset)
        total_loss = 0.0
        num_batches = (num_samples + effective_batch_size - 1) // effective_batch_size

        pbar = tqdm(range(0, num_samples, effective_batch_size), desc=f"Epoch {epoch+1}/{EPOCHS}", total=num_batches)
        for i in pbar:
            batch = dataset[i:min(i + effective_batch_size, num_samples)]
            if not batch: continue

            # Prepare Batch (Move to Device)
            batch_states_np = np.array([s for (s, _, _) in batch], dtype=np.float32)
            batch_states = torch.tensor(batch_states_np).to(device)
            batch_actions = torch.tensor([a for (_, a, _) in batch], dtype=torch.long).to(device)
            batch_rewards = torch.tensor([r for (_, _, r) in batch], dtype=torch.float32).to(device)

            # Forward -> Loss -> Backward -> Optimize
            outputs = model(batch_states)
            action_preds = outputs.gather(1, batch_actions.unsqueeze(1)).squeeze(1)
            loss = loss_fn(action_preds, batch_rewards)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            pbar.set_postfix({"Loss": f"{loss.item():.4f}"})

        avg_loss = total_loss / max(1, num_batches)
        logging.info(f"Epoch {epoch+1} completed. Avg Loss = {avg_loss:.6f}")
    #  End Training Loop 

    # Save Model Weights
    os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
    try:
        model.to('cpu'); torch.save(model.state_dict(), WEIGHTS_PATH); logging.info(f"Model weights saved to {WEIGHTS_PATH}."); model.to(device);
    except Exception as e: logging.error(f"Error saving model weights: {e}")

if __name__ == "__main__":
    mode = "train"
    if len(sys.argv) > 1:
        arg_mode = sys.argv[1].lower()
        if arg_mode in ["train", "play"]: mode = arg_mode
        else: logging.warning(f"Invalid mode '{sys.argv[1]}'. Using default 'train'.")
    train(mode)