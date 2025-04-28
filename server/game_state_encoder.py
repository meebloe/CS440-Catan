# server/game_state_encoder.py

import numpy as np
import logging

# --- Constants and Mappings ---

# Define resource order consistently
# RESOURCE_ORDER = ["LUMBER", "BRICK", "WOOL", "GRAIN", "ORE"] # Old
RESOURCE_ORDER = ["WOOD", "BRICK", "SHEEP", "WHEAT", "STONE"]
NUM_RESOURCES = len(RESOURCE_ORDER)

# Define building types order consistently
BUILDING_TYPES = ["NONE", "SETTLEMENT", "CITY"] # For player-agnostic type
NUM_BUILDING_TYPES = len(BUILDING_TYPES)


MAX_RESOURCES_PER_TYPE = 19 # Theoretical max, practical is lower
MAX_VICTORY_POINTS = 10 # Or slightly higher for edge cases

# Define fixed counts based on standard Catan rules
NUM_HEXES = 19
NUM_ROADS = 72
NUM_INTERSECTIONS = 54
NUM_PLAYERS = 2 # Specific to your 2-player setup

# --- Vector Section Size Calculation ---
# Helps prevent errors if you change features

# Hexes: (one-hot resource + number token)
# One-hot for 6 types (5 resources + desert) = 6 features
# Number token (0-1, or 0 if desert/none) = 1 feature
FEATURES_PER_HEX = 6 + 1
HEX_SECTION_SIZE = NUM_HEXES * FEATURES_PER_HEX # 19 * 7 = 133

# Roads: (owner: empty, p0, p1) -> one-hot encoding
FEATURES_PER_ROAD = NUM_PLAYERS + 1 # +1 for empty
ROAD_SECTION_SIZE = NUM_ROADS * FEATURES_PER_ROAD # 72 * 3 = 216

# Buildings: (owner: empty, p0, p1) + (type: none, settlement, city) -> two one-hot vectors concatenated
FEATURES_PER_BUILDING_OWNER = NUM_PLAYERS + 1 # +1 for empty
FEATURES_PER_BUILDING_TYPE = NUM_BUILDING_TYPES # None, Settlement, City
FEATURES_PER_BUILDING = FEATURES_PER_BUILDING_OWNER + FEATURES_PER_BUILDING_TYPE
BUILDING_SECTION_SIZE = NUM_INTERSECTIONS * FEATURES_PER_BUILDING # 54 * (3 + 3) = 324

# Player Info (Per Player): Resources + VP
FEATURES_PER_PLAYER = NUM_RESOURCES + 1 # 5 resources + 1 VP
PLAYER_SECTION_SIZE = NUM_PLAYERS * FEATURES_PER_PLAYER # 2 * (5 + 1) = 12

# Global Info: Current Player Index + Dice Roll (single int)
# Dice is scaled between 2–12 (mapped to 0–1)
GLOBAL_FEATURES_SIZE = 1 + 1  # currentPlayerIndex + diceResult

# --- Total Vector Size ---
TOTAL_VECTOR_SIZE = (
    HEX_SECTION_SIZE +
    ROAD_SECTION_SIZE +
    BUILDING_SECTION_SIZE +
    PLAYER_SECTION_SIZE +
    GLOBAL_FEATURES_SIZE
) # 133 + 216 + 324 + 12 + 2 = 687


logging.info(f"Calculated total state vector size: {TOTAL_VECTOR_SIZE}")

# Resource to index mapping for one-hot encoding
RESOURCE_TO_INDEX = {res: i for i, res in enumerate(RESOURCE_ORDER)}
# Add Desert for hex encoding
HEX_RESOURCE_TYPES = RESOURCE_ORDER + ["DESERT"]
HEX_RES_TO_INDEX = {res: i for i, res in enumerate(HEX_RESOURCE_TYPES)}

# Building type to index mapping
BUILDING_TYPE_TO_INDEX = {btype: i for i, btype in enumerate(BUILDING_TYPES)}


def vectorize_state(state_data: dict) -> np.ndarray:
    """
    Converts the Catan game state dictionary (from JSON) into a fixed-size NumPy vector.

    Args:
        state_data: A dictionary representing the game state, matching the JSON structure.

    Returns:
        A NumPy array representing the vectorized state, or None if input is invalid.
    """
    if not state_data:
        logging.error("Received empty state_data for vectorization.")
        return None

    # Initialize the vector with zeros
    state_vector = np.zeros(TOTAL_VECTOR_SIZE, dtype=np.float32)
    current_offset = 0

    # --- 1. Hex Information ---
    try:
        hexes = state_data.get('hexes', [])
        if len(hexes) != NUM_HEXES:
            logging.warning(f"Expected {NUM_HEXES} hexes, but found {len(hexes)}. Skipping hex encoding.")
        else:
            for i, hex_info in enumerate(hexes):
                hex_offset = current_offset + i * FEATURES_PER_HEX

                # One-hot encode resource type (including Desert)
                res_type = hex_info.get("resource", "DESERT") # Default to DESERT if missing
                res_idx = HEX_RES_TO_INDEX.get(res_type, len(HEX_RESOURCE_TYPES) - 1) # Default to last index (Desert)
                state_vector[hex_offset + res_idx] = 1.0

                # Normalize number token (scale 2-12 to approx 0-1, 0 if null/desert)
                number_token = hex_info.get("numberToken")
                # Simple scaling: (token - 2) / 10. Max (12) -> 1.0, Min (2) -> 0.0. Others in between.
                # Treat 7 (desert/no token) as 0.
                scaled_token = 0.0
                if number_token and number_token != 7:
                    scaled_token = max(0.0, min(1.0, (number_token - 2.0) / 10.0))
                state_vector[hex_offset + len(HEX_RESOURCE_TYPES)] = scaled_token

        current_offset += HEX_SECTION_SIZE

    except Exception as e:
        logging.exception(f"Error vectorizing hexes: {e}")
        # Decide if you want to return None or continue with a potentially incomplete vector
        current_offset += HEX_SECTION_SIZE # Ensure offset progresses even on error


    # --- 2. Road Information ---
    try:
        roads = state_data.get('roads', [])
        if len(roads) != NUM_ROADS:
             logging.warning(f"Expected {NUM_ROADS} roads, but found {len(roads)}. Skipping road encoding.")
        else:
            for i, road_info in enumerate(roads):
                road_offset = current_offset + i * FEATURES_PER_ROAD
                owner_idx = road_info.get("ownerPlayerIndex", -1)

                # One-hot: Index 0 = empty, Index 1 = player 0, Index 2 = player 1
                if owner_idx == -1:
                    state_vector[road_offset + 0] = 1.0
                elif 0 <= owner_idx < NUM_PLAYERS:
                    state_vector[road_offset + 1 + owner_idx] = 1.0
                else:
                    logging.warning(f"Invalid road owner index {owner_idx} for road {i}. Treating as empty.")
                    state_vector[road_offset + 0] = 1.0 # Default to empty

        current_offset += ROAD_SECTION_SIZE
    except Exception as e:
        logging.exception(f"Error vectorizing roads: {e}")
        current_offset += ROAD_SECTION_SIZE


    # --- 3. Building Information ---
    try:
        buildings = state_data.get('buildings', [])
        if len(buildings) != NUM_INTERSECTIONS:
            logging.warning(f"Expected {NUM_INTERSECTIONS} buildings, but found {len(buildings)}. Skipping building encoding.")
        else:
            for i, building_info in enumerate(buildings):
                building_offset = current_offset + i * FEATURES_PER_BUILDING
                owner_idx = building_info.get("ownerPlayerIndex", -1)
                building_type_str = building_info.get("type", "NONE") # Default to NONE

                # One-hot encode owner (Index 0=empty, 1=p0, 2=p1)
                if owner_idx == -1:
                    state_vector[building_offset + 0] = 1.0
                elif 0 <= owner_idx < NUM_PLAYERS:
                    state_vector[building_offset + 1 + owner_idx] = 1.0
                else:
                    logging.warning(f"Invalid building owner index {owner_idx} for building {i}. Treating as empty.")
                    state_vector[building_offset + 0] = 1.0 # Default to empty

                # One-hot encode building type (Index 0=NONE, 1=SETTLEMENT, 2=CITY)
                # Starting offset after the owner part
                type_offset = building_offset + FEATURES_PER_BUILDING_OWNER
                type_idx = BUILDING_TYPE_TO_INDEX.get(building_type_str, 0) # Default to NONE index (0)
                state_vector[type_offset + type_idx] = 1.0

        current_offset += BUILDING_SECTION_SIZE
    except Exception as e:
        logging.exception(f"Error vectorizing buildings: {e}")
        current_offset += BUILDING_SECTION_SIZE


    # --- 4. Player Information ---
    try:
        players = state_data.get('players', [])
        if len(players) != NUM_PLAYERS:
            logging.warning(f"Expected {NUM_PLAYERS} players, but found {len(players)}. Skipping player encoding.")
        else:
            for i, player_info in enumerate(players):
                player_offset = current_offset + i * FEATURES_PER_PLAYER

                # Resources (using RESOURCE_ORDER)
                resources = player_info.get("resources", {})
                for j, res_name in enumerate(RESOURCE_ORDER):
                    count = resources.get(res_name, 0)
                    state_vector[player_offset + j] = min(count, MAX_RESOURCES_PER_TYPE) / MAX_RESOURCES_PER_TYPE

                # Victory Points (normalize)
                vp = player_info.get("victoryPoints", 0)
                state_vector[player_offset + NUM_RESOURCES] = min(vp, MAX_VICTORY_POINTS) / MAX_VICTORY_POINTS

        current_offset += PLAYER_SECTION_SIZE
    except Exception as e:
        logging.exception(f"Error vectorizing players: {e}")
        current_offset += PLAYER_SECTION_SIZE


    # --- 5. Global Information ---
    try:
        current_player_idx = state_data.get("currentPlayerIndex", 0)
        state_vector[current_offset + 0] = float(current_player_idx)

        dice_result = state_data.get("diceResult", 0)
        if isinstance(dice_result, int) and 2 <= dice_result <= 12:
            state_vector[current_offset + 1] = (dice_result - 2.0) / 10.0
        else:
            state_vector[current_offset + 1] = 0.0

        current_offset += GLOBAL_FEATURES_SIZE

    except Exception as e:
        logging.exception(f"Error vectorizing global info: {e}")
        current_offset += GLOBAL_FEATURES_SIZE

    # --- Final Check ---
    if current_offset != TOTAL_VECTOR_SIZE:
         logging.error(f"Vectorization finished at offset {current_offset}, but expected size {TOTAL_VECTOR_SIZE}. There might be an implementation error.")
         # Handle this error appropriately - maybe return None or raise an exception

    # logging.debug(f"Final state vector (first 20 elements): {state_vector[:20]}") # For debugging
    return state_vector

# --- Example Usage (for testing this file directly) ---
if __name__ == "__main__":
    print(f"State vector total size: {TOTAL_VECTOR_SIZE}")

    # Create a dummy state matching the structure used by test_client.py
    dummy_state_example = {
        "gameStateId": "dummy_test_1",
        "currentPlayerIndex": 0,
        "diceResult": 4,
        "hexes": [{"id": i, "resource": random.choice(HEX_RESOURCE_TYPES), "numberToken": random.choice([2,3,4,5,6,8,9,10,11,12, None])} for i in range(NUM_HEXES)],
        "roads": [{"id": i, "ownerPlayerIndex": random.choice([-1, 0, 1])} for i in range(NUM_ROADS)],
        "buildings": [{"id": i, "ownerPlayerIndex": random.choice([-1, 0, 1]), "type": random.choice(BUILDING_TYPES)} for i in range(NUM_INTERSECTIONS)],
        "players": [
            {"index": 0, "resources": {"LUMBER": 2, "BRICK": 1, "WOOL": 0, "GRAIN": 3, "ORE": 0}, "victoryPoints": 3},
            {"index": 1, "resources": {"LUMBER": 1, "BRICK": 0, "WOOL": 4, "GRAIN": 1, "ORE": 2}, "victoryPoints": 4}
        ],
        "availableActions": [] # Not used by vectorization, but part of the state
    }
    import random # Need random for the example state generation

    print("\nTesting vectorization with dummy data:")
    vector = vectorize_state(dummy_state_example)

    if vector is not None:
        print(f"Successfully generated vector of size: {vector.shape}")
        # print("Sample vector elements:")
        # print(vector[150:170]) # Print a small slice
    else:
        print("Vectorization failed.")