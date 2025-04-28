# server/model.py

import torch
import torch.nn as nn
import torch.nn.functional as F
import logging
import random
# Need action mapping for predict_action
try:
    # Adjust relative imports if running directly vs as part of a package
    if __package__:
        from .action_mapping import get_action_index, TOTAL_ACTIONS
        from .game_state_encoder import TOTAL_VECTOR_SIZE # Import constant
    else:
        from action_mapping import get_action_index, TOTAL_ACTIONS
        from game_state_encoder import TOTAL_VECTOR_SIZE
except ImportError as e:
     # Fallback if direct run or structure issues
     logging.warning(f"Model Import Warning: {e}. Using hardcoded constants.")
     TOTAL_VECTOR_SIZE = 687
     TOTAL_ACTIONS = 201
     def get_action_index(action_dict): return None # Placeholder


#  Define the Neural Network 
class CatanSimpleMLP(nn.Module):
    """
    A Multi-Layer Perceptron with Dropout for Catan state evaluation.
    Input: Flattened state vector.
    Output: Scores for each possible theoretical action.
    """

    def __init__(self, input_size=TOTAL_VECTOR_SIZE, output_size=TOTAL_ACTIONS,
                 hidden_size1=512, hidden_size2=256, dropout_prob=0.3):
        super(CatanSimpleMLP, self).__init__()
        self.input_size = input_size
        self.output_size = output_size
        self.dropout_prob = dropout_prob

        self.fc1 = nn.Linear(input_size, hidden_size1)
        self.fc2 = nn.Linear(hidden_size1, hidden_size2)
        self.fc3 = nn.Linear(hidden_size2, output_size)  # Output layer size = total possible actions

        # Dropout layer (not sure if we really need this)
        self.dropout = nn.Dropout(p=self.dropout_prob)

        # Epsilon-greedy exploration (percent as decimal)
        self.epsilon = 0.15 # Percentage chance to take a random action (explore)

        logging.info(
            f"Initialized CatanSimpleMLP: Input={input_size}, "
            f"Hidden=[{hidden_size1}, {hidden_size2}], Output={output_size}, "
            f"Dropout={dropout_prob}" # Log dropout
        )

    def forward(self, x):
        """
        Forward pass through the network. Includes Dropout if training.
        """
        if not isinstance(x, torch.Tensor):
            # Convert numpy array or list to tensor if not already
            x = torch.tensor(x, dtype=torch.float32)

        # Ensure input is 2D (batch_size, input_size)
        if x.dim() == 1:
            x = x.unsqueeze(0)
        elif x.dim() > 2:
             x = x.view(x.size(0), -1) # Flatten features


        #  Apply layers with activation and Dropout 
        x = F.relu(self.fc1(x))
        x = self.dropout(x) # Apply dropout after activation
        x = F.relu(self.fc2(x))
        x = self.dropout(x) # Apply dropout after activation
        x = self.fc3(x) # Scores for each action

        return x

    #  predict_action method remains the same 
    def predict_action(self, state_tensor, available_actions, use_exploration=True):
        """
        Given a state tensor and available actions, predict the best action index.
        Uses epsilon-greedy exploration during inference if enabled.
        IMPORTANT: Assumes model is already in eval() mode and state_tensor is on the correct device.
        """

        with torch.no_grad():

            model_output = self.forward(state_tensor) # Uses the updated forward pass

            if not available_actions:
                logging.warning("predict_action called with no available actions.")
                return None

            #  Exploration
            if use_exploration and random.random() < self.epsilon:
                random_action = random.choice(available_actions)
                return random_action

            #  Otherwise pick best-scoring available action 
            best_score = -float('inf')
            chosen_action = None
            scores = model_output.squeeze(0) # Remove batch dimension

            available_indices = []
            action_map = {}
            for action_dict in available_actions:
                action_idx = get_action_index(action_dict)
                if action_idx is not None and 0 <= action_idx < self.output_size:
                     available_indices.append(action_idx)
                     action_map[action_idx] = action_dict # Map index back to dict

            if not available_indices:
                 logging.error("No available actions could be mapped to valid indices!")
                 end_turn_action = next((a for a in available_actions if a.get("actionType") == "END_TURN"), None)
                 return end_turn_action # Return END_TURN if found, else None

            # Efficiently find best score among available actions using tensor operations
            available_scores = scores[available_indices] # Get scores only for available actions
            best_local_idx = torch.argmax(available_scores).item() # Index within available_scores
            best_global_idx = available_indices[best_local_idx] # Map back to global action index
            chosen_action = action_map[best_global_idx]
            # best_score = available_scores[best_local_idx].item()

            # logging.debug(f"Chosen action: {chosen_action} with score {best_score:.4f}")
            return chosen_action


#  Example Usage (for testing this file directly) 
if __name__ == "__main__":
    print("Testing updated model definition...")
    # Test instantiation with new defaults
    model = CatanSimpleMLP()
    print(model)

    # Create dummy input matching TOTAL_VECTOR_SIZE
    # Use the imported or fallback constant
    dummy_input = torch.randn(TOTAL_VECTOR_SIZE)
    print(f"\nDummy input shape: {dummy_input.shape}")

    # Set to eval mode for testing inference (disables dropout)
    model.eval()
    with torch.no_grad():
        output = model(dummy_input)

    print(f"Output shape: {output.shape}") # Should be [1, TOTAL_ACTIONS]
    print(f"Sample output scores (first 10): {output[0, :10].tolist()}")

    # Example of calling predict_action (needs dummy available actions)
    print("\nTesting predict_action:")
    dummy_actions = [
        {"actionType": "BUILD_ROAD", "edgeIndex": 5}, # Index 5
        {"actionType": "END_TURN"} # Index 200 (based on previous mapping)
    ]
    # Map END_TURN index correctly if possible, otherwise use fallback
    end_turn_idx_fallback = 200
    end_turn_idx = get_action_index({"actionType": "END_TURN"}) or end_turn_idx_fallback

    if get_action_index is None: # If imports failed
         print("Skipping predict_action test due to import issues.")
    else:
        # Simulate available actions matching the indices
        test_actions = [
            {"actionType": "BUILD_ROAD", "edgeIndex": 5},
            {"actionType": "END_TURN"}
        ]
        # Make sure the model instance exists and is in eval mode
        model.eval()
        chosen = model.predict_action(dummy_input, test_actions, use_exploration=False)
        print(f"Predicted action (no exploration): {chosen}")

        chosen_explore = model.predict_action(dummy_input, test_actions, use_exploration=True)
        print(f"Predicted action (with exploration): {chosen_explore}")