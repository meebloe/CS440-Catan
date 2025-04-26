# server/catan_ai.py

from flask import Flask, request, jsonify
from typing import Optional
import random
import logging
import json
import numpy as np
import os
import torch # Added PyTorch

# Import from our custom modules
try:
    from .game_state_encoder import vectorize_state, TOTAL_VECTOR_SIZE
    from .action_mapping import get_action_index, TOTAL_ACTIONS # Import mapping functions
    from .model import CatanSimpleMLP # Import the model class
except ImportError:
    from game_state_encoder import vectorize_state, TOTAL_VECTOR_SIZE
    from action_mapping import get_action_index, TOTAL_ACTIONS
    from model import CatanSimpleMLP

# --- Flask App Setup ---
app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
app.logger.info("Flask app initialized.")

# --- Load/Initialize the Model ---
# Instantiate the model with random weights
# Note: For actual training, you'd load saved weights here.
model = CatanSimpleMLP(input_size=TOTAL_VECTOR_SIZE, output_size=TOTAL_ACTIONS)
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "model_weights.pth")

if os.path.exists(WEIGHTS_PATH):
    model.load_state_dict(torch.load(WEIGHTS_PATH))
    app.logger.info("Loaded existing model weights.")
else:
    app.logger.info("No existing model weights found. Starting fresh.")
model.eval() # Set the model to evaluation mode (important!)
app.logger.info(f"Initialized/Loaded CatanSimpleMLP model. Ready for inference.")
# ---------------------------------

def select_action_from_model(model_output: torch.Tensor, available_actions: list) -> Optional[dict]:
    """
    Selects the best *available* action based on model scores.

    Args:
        model_output: The raw output tensor from the model (scores for all possible actions). Shape [1, TOTAL_ACTIONS].
        available_actions: The list of action dictionaries received from Unity.

    Returns:
        The chosen action dictionary, or None if no valid action can be selected.
    """
    if not available_actions:
        app.logger.warning("select_action_from_model called with no available actions.")
        return None

    # Get scores for all actions (remove batch dimension)
    action_scores = model_output.squeeze(0) # Shape [TOTAL_ACTIONS]

    best_score = -float('inf')
    chosen_action = None
    valid_indices_scores = [] # For debugging/logging

    for action_dict in available_actions:
        action_idx = get_action_index(action_dict)

        if action_idx is not None and 0 <= action_idx < TOTAL_ACTIONS:
            score = action_scores[action_idx].item() # Get score for this specific action index
            valid_indices_scores.append((action_idx, score, action_dict['actionType'])) # Log index, score, type

            if score > best_score:
                best_score = score
                chosen_action = action_dict
        else:
            app.logger.warning(f"Could not map or invalid index for available action: {action_dict}")

    # Log the scores of considered available actions
    app.logger.debug(f"Scores for available actions (Index, Score, Type): {valid_indices_scores}")

    if chosen_action:
        app.logger.info(f"Action selected by model: {chosen_action} (Score: {best_score:.4f})")
    else:
        # Fallback if no valid action could be processed (should be rare)
        app.logger.error("Failed to select any action from model output based on available actions. Falling back.")
        # Maybe pick random from available as fallback? Or return error?
        chosen_action = random.choice(available_actions) if available_actions else None

    return chosen_action


@app.route('/get_action', methods=['POST'])
def get_action():
    """
    Receives game state, vectorizes it, feeds to model, selects best
    available action based on model scores, and returns it.
    """
    app.logger.debug("'/get_action' endpoint hit.")

    if not request.is_json:
        app.logger.error("Request received was not JSON")
        return jsonify({"error": "Request must be JSON"}), 400

    state_vector = None
    try:
        state_data = request.get_json()
        app.logger.info(f"Received state for player {state_data.get('currentPlayerIndex', 'N/A')}")

        # --- Step 1: Vectorize the State ---
        app.logger.debug("Attempting to vectorize state...")
        state_vector = vectorize_state(state_data)

        if state_vector is None or state_vector.shape[0] != TOTAL_VECTOR_SIZE:
             # Error logging handled within vectorize_state or below
             app.logger.error("State vectorization failed or size mismatch.")
             return jsonify({"error": "State vectorization failed or size mismatch."}), 500
        else:
             app.logger.info(f"State successfully vectorized. Vector shape: {state_vector.shape}")
             app.logger.debug(f"Vector sample (first 10): {state_vector[:10]}")
        # ------------------------------------


        # --- Step 2: Get Model Prediction ---
        app.logger.debug("Getting prediction from model...")
        try:
            # Convert numpy array to torch tensor before passing to model
            state_tensor = torch.tensor(state_vector, dtype=torch.float32)
            with torch.no_grad(): # Ensure no gradients are computed during inference
                 model_output = model(state_tensor) # Pass tensor to model
            app.logger.debug(f"Model output tensor shape: {model_output.shape}") # Should be [1, TOTAL_ACTIONS]
            # Log a sample of raw scores
            app.logger.debug(f"Raw model output scores sample (first 10): {model_output.squeeze(0)[:10].tolist()}")
        except Exception as model_err:
            app.logger.exception("Error during model prediction:")
            return jsonify({"error": "Failed during model inference", "details": str(model_err)}), 500
        # ------------------------------------


        # --- Step 3: Select Action (Using availableActions Mask & Model Scores) ---
        available_actions = state_data.get('availableActions')
        app.logger.debug(f"Available actions received: {available_actions}")

        chosen_action = select_action_from_model(model_output, available_actions)
        # --------------------------------------------------------------------


        # --- Step 4: Return Chosen Action ---
        if chosen_action:
            app.logger.debug(f"Returning action: {json.dumps(chosen_action)}")
            return jsonify(chosen_action)
        else:
            app.logger.error("No action could be selected. Returning error.")
            return jsonify({"error": "Failed to select a valid action."}), 500
        # ---------------------------------

    except Exception as e:
        app.logger.exception("An internal server error occurred processing the '/get_action' request:")
        return jsonify({"error": "An internal server error occurred", "details": str(e)}), 500


if __name__ == '__main__':
    app.logger.info("Starting Catan AI Flask server (with NN model integration)...")
    app.run(host='0.0.0.0', port=5000, debug=True) # Use debug=True for development changes