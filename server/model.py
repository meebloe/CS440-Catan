# server/model.py

import torch
import torch.nn as nn
import torch.nn.functional as F
import logging
import random
from action_mapping import get_action_index

# --- Import constants from other modules ---
try:
    from .game_state_encoder import TOTAL_VECTOR_SIZE
    from .action_mapping import TOTAL_ACTIONS
except ImportError:
    from game_state_encoder import TOTAL_VECTOR_SIZE
    from action_mapping import TOTAL_ACTIONS

# --- Define the Neural Network ---
class CatanSimpleMLP(nn.Module):
    """
    A simple Multi-Layer Perceptron for Catan state evaluation.
    Input: Flattened state vector.
    Output: Scores for each possible theoretical action.
    """
    def __init__(self, input_size=TOTAL_VECTOR_SIZE, output_size=TOTAL_ACTIONS, hidden_size1=256, hidden_size2=128):
        super(CatanSimpleMLP, self).__init__()
        self.input_size = input_size
        self.output_size = output_size

        self.fc1 = nn.Linear(input_size, hidden_size1)
        self.fc2 = nn.Linear(hidden_size1, hidden_size2)
        self.fc3 = nn.Linear(hidden_size2, output_size)  # Output layer size = total possible actions

        # Epsilon-greedy exploration
        self.epsilon = 0.15

        logging.info(f"Initialized CatanSimpleMLP: Input={input_size}, Hidden=[{hidden_size1}, {hidden_size2}], Output={output_size}")

    def forward(self, x):
        """
        Forward pass through the network (for training).
        """
        if not isinstance(x, torch.Tensor):
            x = torch.tensor(x, dtype=torch.float32)

        if x.dim() == 1:
            x = x.unsqueeze(0)  # Add batch dimension if necessary

        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x

    def predict_action(self, state_tensor, available_actions, use_exploration=True):
        """
        Given a state tensor and available actions, predict the best action index.
        Uses epsilon-greedy exploration during inference if enabled.
        """
        self.eval()
        with torch.no_grad():
            model_output = self.forward(state_tensor)

            if not available_actions:
                return None

            # --- Exploration (epsilon-greedy) ---
            if use_exploration and random.random() < self.epsilon:
                random_action = random.choice(available_actions)
                print("Exploration: Random action selected during inference.")
                return random_action

            # --- Otherwise pick best-scoring action ---
            best_score = -float('inf')
            chosen_action = None
            scores = model_output.squeeze(0)  # Remove batch dimension

            for action_dict in available_actions:
                action_idx = get_action_index(action_dict)
                if action_idx is not None and 0 <= action_idx < TOTAL_ACTIONS:
                    score = scores[action_idx].item()
                    if score > best_score:
                        best_score = score
                        chosen_action = action_dict

            return chosen_action

# --- Example Usage (for testing this file directly) ---
if __name__ == "__main__":
    print("Testing model definition...")
    model = CatanSimpleMLP()
    print(model)

    dummy_input = torch.randn(TOTAL_VECTOR_SIZE)
    print(f"\nDummy input shape: {dummy_input.shape}")

    model.eval()
    with torch.no_grad():
        output = model(dummy_input)

    print(f"Output shape: {output.shape}")
    print(f"Sample output scores (first 10): {output[0, :10]}")