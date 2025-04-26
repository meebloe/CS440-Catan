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

# --- Determine Mode (Train or Play) ---
# Default to play mode unless explicitly set via environment variable
TRAIN_MODE = os.environ.get("CATAN_TRAIN_MODE", "0") == "1"
app.logger.info(f"Server running in {'TRAIN' if TRAIN_MODE else 'PLAY'} mode.")

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
# ----------------------------------

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


        # --- Step 3: Select Action (Using Model.predict_action which handles epsilon-greedy) ---
        available_actions = state_data.get('availableActions')
        app.logger.debug(f"Available actions received: {available_actions}")

        chosen_action = model.predict_action(state_tensor, available_actions, use_exploration=TRAIN_MODE)
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