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
app.logger.setLevel(logging.INFO)
app.logger.info("Flask app initialized.")

# --- Determine Mode (Train or Play) ---
TRAIN_MODE = os.environ.get("CATAN_TRAIN_MODE", "0") == "1"
app.logger.info(f"Server running in {'TRAIN' if TRAIN_MODE else 'PLAY'} mode.")

# --- Determine Device (CUDA or CPU) ---
if torch.cuda.is_available():
    device = torch.device("cuda")
    app.logger.info("CUDA is available! Using GPU for inference.")
else:
    device = torch.device("cpu")
    app.logger.info("CUDA not available. Using CPU for inference.")
# --------------------------------------

# --- Load/Initialize the Model ---
model = CatanSimpleMLP(input_size=TOTAL_VECTOR_SIZE, output_size=TOTAL_ACTIONS)
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "model_weights.pth")

if os.path.exists(WEIGHTS_PATH):
    try:
        # Load weights onto the correct device directly
        model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
        app.logger.info(f"Loaded existing model weights onto {device}.")
    except Exception as e:
        app.logger.error(f"Error loading weights: {e}. Starting with fresh weights on {device}.")
else:
    app.logger.info(f"No existing model weights found. Starting fresh on {device}.")

# --- Move Model to Device ---
model.to(device)
# ---------------------------

model.eval() # Set the model to evaluation mode (important!)
app.logger.info(f"Initialized/Loaded CatanSimpleMLP model on {device}. Ready for inference.")
# ----------------------------------

@app.route('/get_action', methods=['POST'])
def get_action():
    """
    Receives game state, vectorizes it, feeds to model (on GPU/CPU), selects best
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

        # --- Step 1: Vectorize the State (remains on CPU) ---
        app.logger.debug("Attempting to vectorize state...")
        state_vector = vectorize_state(state_data)

        if state_vector is None or state_vector.shape[0] != TOTAL_VECTOR_SIZE:
             app.logger.error("State vectorization failed or size mismatch.")
             return jsonify({"error": "State vectorization failed or size mismatch."}), 500
        else:
             app.logger.info(f"State successfully vectorized. Vector shape: {state_vector.shape}")
             # app.logger.debug(f"Vector sample (first 10): {state_vector[:10]}") # Keep debugging if needed

        # --- Step 2: Get Model Prediction ---
        app.logger.debug("Getting prediction from model...")
        try:
            # --- Convert numpy array to torch tensor AND move to device ---
            state_tensor = torch.tensor(state_vector, dtype=torch.float32).to(device)
            # ---------------------------------------------------------------

            with torch.no_grad(): # Ensure no gradients are computed during inference
                 # Model is already on the device, tensor is moved, computation happens on device
                 model_output = model(state_tensor)
            app.logger.debug(f"Model output tensor shape: {model_output.shape}")

            # --- Move output back to CPU for further processing if needed (predict_action handles .item()) ---
            # model_output_cpu = model_output.cpu() # Usually not needed if predict_action uses .item()
            # app.logger.debug(f"Raw model output scores sample (first 10): {model_output_cpu.squeeze(0)[:10].tolist()}")
            app.logger.debug(f"Raw model output scores sample (first 10, from device): {model_output.squeeze(0)[:10].tolist()}")


        except Exception as model_err:
            app.logger.exception("Error during model prediction:")
            return jsonify({"error": "Failed during model inference", "details": str(model_err)}), 500
        # ------------------------------------

        # --- Step 3: Select Action (Using Model.predict_action which handles epsilon-greedy) ---
        available_actions = state_data.get('availableActions')
        app.logger.debug(f"Available actions received: {available_actions}")

        # Pass the state_tensor (which is already on the correct device)
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
    # Consider disabling debug=True for production/stable use
    app.run(host='0.0.0.0', port=5000, debug=False) # Changed debug to False