# server/catan_ai.py

from flask import Flask, request, jsonify
from typing import Optional
import random
import logging
import json
import numpy as np
import os
import torch

# Import from custom modules
try:
    # Use relative imports if part of a package
    from .game_state_encoder import vectorize_state, TOTAL_VECTOR_SIZE
    from .action_mapping import get_action_index, TOTAL_ACTIONS
    from .model import CatanSimpleMLP
except ImportError:
    # Fallback for running script directly
    from game_state_encoder import vectorize_state, TOTAL_VECTOR_SIZE
    from action_mapping import get_action_index, TOTAL_ACTIONS
    from model import CatanSimpleMLP

#  Flask App Setup 
app = Flask(__name__)
app.logger.setLevel(logging.INFO) # Set to debug for more verbosity

#  Configuration 
TRAIN_MODE = os.environ.get("CATAN_TRAIN_MODE", "0") == "1"
app.logger.info(f"Server running in {'TRAIN' if TRAIN_MODE else 'PLAY'} mode.")

if torch.cuda.is_available():
    device = torch.device("cuda")
    app.logger.info("Using GPU for inference.")
else:
    device = torch.device("cpu")
    app.logger.info("Using CPU for inference.")

#  Model Initialization 
model = CatanSimpleMLP(input_size=TOTAL_VECTOR_SIZE, output_size=TOTAL_ACTIONS)
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "model_weights.pth")

if os.path.exists(WEIGHTS_PATH):
    try:
        model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
        app.logger.info(f"Loaded existing model weights from {WEIGHTS_PATH} onto {device}.")
    except Exception as e:
        app.logger.error(f"Error loading weights from {WEIGHTS_PATH}: {e}. Starting fresh.")
else:
    app.logger.info(f"No weights found at {WEIGHTS_PATH}. Starting fresh.")

model.to(device)
model.eval() # Set to evaluation mode
app.logger.info(f"Model ready on {device}.")

@app.route('/get_action', methods=['POST'])
def get_action():
    """Receives game state, predicts best available action, returns it."""

    if not request.is_json:
        app.logger.error("Request received was not JSON")
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        state_data = request.get_json()
        app.logger.debug(f"Received state for player {state_data.get('currentPlayerIndex', 'N/A')}")

        state_vector = vectorize_state(state_data)
        if state_vector is None or state_vector.shape[0] != TOTAL_VECTOR_SIZE:
             app.logger.error("State vectorization failed or produced incorrect size.")
             return jsonify({"error": "State vectorization failed"}), 500

        try:
            state_tensor = torch.tensor(state_vector, dtype=torch.float32).to(device)
            with torch.no_grad():
                 model_output = model(state_tensor)
            app.logger.debug(f"Model output tensor shape: {model_output.shape}")
            app.logger.debug(f"Raw scores sample: {model_output.squeeze(0)[:10].tolist()}")

        except Exception as model_err:
            app.logger.exception("Error during model prediction:") # Log full traceback
            return jsonify({"error": "Model inference failed", "details": str(model_err)}), 500

        available_actions = state_data.get('availableActions')
        if not available_actions: # Check if list exists and is not empty
            app.logger.warning("Received state with no available actions.")
            return jsonify({"error": "No available actions provided in state"}), 400

        app.logger.debug(f"Available actions: {available_actions}")
        chosen_action = model.predict_action(state_tensor, available_actions, use_exploration=TRAIN_MODE)

        if chosen_action:
            app.logger.info(f"P{state_data.get('currentPlayerIndex', '?')} Action: {chosen_action.get('actionType', 'Unknown')}")
            return jsonify(chosen_action)
        else:
            # This should ideally not happen if available_actions is not empty and mapping works
            app.logger.error("Model.predict_action failed to select an action.")
            return jsonify({"error": "Failed to select a valid action"}), 500

    except Exception as e:
        app.logger.exception("Internal server error processing '/get_action':")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == '__main__':
    app.logger.info("Starting Catan AI Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=False)