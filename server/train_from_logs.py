import torch
import torch.nn as nn
import torch.optim as optim
import json
import os
import random
import sys
from tqdm import tqdm

from model import CatanSimpleMLP
from game_state_encoder import vectorize_state, TOTAL_VECTOR_SIZE
from action_mapping import get_action_index, TOTAL_ACTIONS

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "..", "client", "SelfPlayLogs")
WEIGHTS_PATH = os.path.join(SCRIPT_DIR, "model_weights.pth")

# --- Hyperparameters ---
NORMAL_LR = 0.001
FAST_LR = 0.01
EPOCHS = 5
BATCH_SIZE = 64

def load_training_data(log_dir):
    states, actions, rewards = [], [], []

    if not os.path.exists(log_dir) or not os.path.isdir(log_dir):
        print(f"[ERROR] Log directory {log_dir} does not exist!")
        return states, actions, rewards

    log_files = [f for f in os.listdir(log_dir) if f.endswith(".jsonl")]
    if not log_files:
        print("[ERROR] No .jsonl files found to train from.")
        return states, actions, rewards

    for file_name in log_files:
        file_path = os.path.join(log_dir, file_name)
        with open(file_path, "r") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines):
            if not line.strip():
                continue

            try:
                game_record = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            winner_index = game_record.get("winnerPlayerIndex")
            turns = game_record.get("turns", [])
            if not turns:
                continue

            for idx, turn in enumerate(turns):
                try:
                    state = turn.get("state")
                    action = turn.get("action")
                    reward = turn.get("reward")

                    if state is None or action is None or reward is None:
                        continue

                    is_last_turn = (idx == len(turns) - 1)
                    is_winner_turn = (state.get("currentPlayerIndex") == winner_index)
                    if is_last_turn and is_winner_turn:
                        reward += 10.0

                    state_vector = vectorize_state(state)
                    if state_vector is None:
                        continue

                    action_idx = get_action_index(action)
                    if action_idx is None:
                        continue

                    states.append(state_vector)
                    actions.append(action_idx)
                    rewards.append(reward)

                except Exception:
                    continue

    return states, actions, rewards

def train(mode="train"):
    if not os.path.exists(LOG_DIR) or not os.path.isdir(LOG_DIR):
        print(f"[ERROR] Log directory {LOG_DIR} does not exist. Nothing to train.")
        return

    states, actions, rewards = load_training_data(LOG_DIR)
    if not states:
        print("[ERROR] No valid training data found.")
        return

    model = CatanSimpleMLP(input_size=TOTAL_VECTOR_SIZE, output_size=TOTAL_ACTIONS)

    if os.path.exists(WEIGHTS_PATH):
        model.load_state_dict(torch.load(WEIGHTS_PATH))
        print("Loaded existing model weights.")
    else:
        print("No existing weights found. Training from scratch.")

    # --- Adjust learning rate based on mode ---
    if mode == "play":
        lr = FAST_LR
        print(f"Running in PLAY mode. Using FAST learning rate {lr}")
    else:
        lr = NORMAL_LR
        print(f"Running in TRAIN mode. Using normal learning rate {lr}")

    model.train()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    dataset = list(zip(states, actions, rewards))

    for epoch in range(EPOCHS):
        random.shuffle(dataset)
        total_loss = 0.0

        for i in tqdm(range(0, len(dataset), BATCH_SIZE), desc=f"Epoch {epoch+1}/{EPOCHS}"):
            batch = dataset[i:i+BATCH_SIZE]

            batch_states = torch.tensor([s for (s, _, _) in batch], dtype=torch.float32)
            batch_actions = torch.tensor([a for (_, a, _) in batch], dtype=torch.long)
            batch_rewards = torch.tensor([r for (_, _, r) in batch], dtype=torch.float32)

            outputs = model(batch_states)
            action_preds = outputs.gather(1, batch_actions.unsqueeze(1)).squeeze(1)

            loss = loss_fn(action_preds, batch_rewards)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / max(1, (len(dataset) / BATCH_SIZE))
        print(f"Epoch {epoch+1} completed. Avg Loss = {avg_loss:.6f}")

    os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
    torch.save(model.state_dict(), WEIGHTS_PATH)
    print("Model weights saved.")

if __name__ == "__main__":
    mode = "train"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    train(mode)