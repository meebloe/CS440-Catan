# server/game_state_encoder.py

import numpy as np
import logging
import random # Needed only for __main__ example

# Constants and Mappings
RESOURCE_ORDER = ["WOOD", "BRICK", "SHEEP", "WHEAT", "STONE"]
NUM_RESOURCES = len(RESOURCE_ORDER)

BUILDING_TYPES = ["NONE", "SETTLEMENT", "CITY"]
NUM_BUILDING_TYPES = len(BUILDING_TYPES)

MAX_RESOURCES_PER_TYPE = 19
MAX_VICTORY_POINTS = 10

NUM_HEXES = 19
NUM_ROADS = 72
NUM_INTERSECTIONS = 54
NUM_PLAYERS = 2

# Vector Section Sizes
FEATURES_PER_HEX = 6 + 1 # one-hot resource + number token
HEX_SECTION_SIZE = NUM_HEXES * FEATURES_PER_HEX

FEATURES_PER_ROAD = NUM_PLAYERS + 1 # one-hot owner (incl. empty)
ROAD_SECTION_SIZE = NUM_ROADS * FEATURES_PER_ROAD

FEATURES_PER_BUILDING_OWNER = NUM_PLAYERS + 1
FEATURES_PER_BUILDING_TYPE = NUM_BUILDING_TYPES
FEATURES_PER_BUILDING = FEATURES_PER_BUILDING_OWNER + FEATURES_PER_BUILDING_TYPE
BUILDING_SECTION_SIZE = NUM_INTERSECTIONS * FEATURES_PER_BUILDING

FEATURES_PER_PLAYER = NUM_RESOURCES + 1 # resources + VP
PLAYER_SECTION_SIZE = NUM_PLAYERS * FEATURES_PER_PLAYER

GLOBAL_FEATURES_SIZE = 1 + 1  # currentPlayerIndex + diceResult

# Total Vector Size
TOTAL_VECTOR_SIZE = (
    HEX_SECTION_SIZE +
    ROAD_SECTION_SIZE +
    BUILDING_SECTION_SIZE +
    PLAYER_SECTION_SIZE +
    GLOBAL_FEATURES_SIZE
)

logging.info(f"Calculated total state vector size: {TOTAL_VECTOR_SIZE}")

# Mappings for Encoding
RESOURCE_TO_INDEX = {res: i for i, res in enumerate(RESOURCE_ORDER)}
HEX_RESOURCE_TYPES = RESOURCE_ORDER + ["DESERT"]
HEX_RES_TO_INDEX = {res: i for i, res in enumerate(HEX_RESOURCE_TYPES)}
BUILDING_TYPE_TO_INDEX = {btype: i for i, btype in enumerate(BUILDING_TYPES)}


def vectorize_state(state_data: dict) -> np.ndarray | None:
    """Converts Catan game state dict into a fixed-size NumPy vector."""
    if not state_data:
        logging.error("Received empty state_data for vectorization.")
        return None

    state_vector = np.zeros(TOTAL_VECTOR_SIZE, dtype=np.float32)
    current_offset = 0

    # Hex Information
    try:
        hexes = state_data.get('hexes', [])
        if len(hexes) == NUM_HEXES:
            for i, hex_info in enumerate(hexes):
                hex_offset = current_offset + i * FEATURES_PER_HEX
                res_type = hex_info.get("resource", "DESERT")
                res_idx = HEX_RES_TO_INDEX.get(res_type, len(HEX_RESOURCE_TYPES) - 1)
                state_vector[hex_offset + res_idx] = 1.0

                number_token = hex_info.get("numberToken")
                scaled_token = 0.0
                if number_token and number_token != 7:
                    scaled_token = max(0.0, min(1.0, (number_token - 2.0) / 10.0))
                state_vector[hex_offset + len(HEX_RESOURCE_TYPES)] = scaled_token
        else:
             logging.warning(f"Expected {NUM_HEXES} hexes, found {len(hexes)}. Skipping hex encoding.")
        current_offset += HEX_SECTION_SIZE
    except Exception as e:
        logging.exception(f"Error vectorizing hexes: {e}")
        return None 

    # Road Information
    try:
        roads = state_data.get('roads', [])
        if len(roads) == NUM_ROADS:
            for i, road_info in enumerate(roads):
                road_offset = current_offset + i * FEATURES_PER_ROAD
                owner_idx = road_info.get("ownerPlayerIndex", -1)
                # One-hot: 0=empty, 1=p0, 2=p1
                if owner_idx == -1:
                    state_vector[road_offset + 0] = 1.0
                elif 0 <= owner_idx < NUM_PLAYERS:
                    state_vector[road_offset + 1 + owner_idx] = 1.0
                else:
                    # Log invalid data but default to empty
                    logging.warning(f"Invalid road owner index {owner_idx} for road {i}. Treating as empty.")
                    state_vector[road_offset + 0] = 1.0
        else:
             logging.warning(f"Expected {NUM_ROADS} roads, found {len(roads)}. Skipping road encoding.")
        current_offset += ROAD_SECTION_SIZE
    except Exception as e:
        logging.exception(f"Error vectorizing roads: {e}")
        return None

    # Building Information
    try:
        buildings = state_data.get('buildings', [])
        if len(buildings) == NUM_INTERSECTIONS:
            for i, building_info in enumerate(buildings):
                building_offset = current_offset + i * FEATURES_PER_BUILDING
                owner_idx = building_info.get("ownerPlayerIndex", -1)
                building_type_str = building_info.get("type", "NONE")

                # One-hot owner
                if owner_idx == -1:
                    state_vector[building_offset + 0] = 1.0
                elif 0 <= owner_idx < NUM_PLAYERS:
                    state_vector[building_offset + 1 + owner_idx] = 1.0
                else:
                    logging.warning(f"Invalid building owner index {owner_idx} for building {i}. Treating as empty.")
                    state_vector[building_offset + 0] = 1.0

                # One-hot building type
                type_offset = building_offset + FEATURES_PER_BUILDING_OWNER
                type_idx = BUILDING_TYPE_TO_INDEX.get(building_type_str, 0) # Default to NONE (idx 0)
                state_vector[type_offset + type_idx] = 1.0
        else:
            logging.warning(f"Expected {NUM_INTERSECTIONS} buildings, found {len(buildings)}. Skipping building encoding.")
        current_offset += BUILDING_SECTION_SIZE
    except Exception as e:
        logging.exception(f"Error vectorizing buildings: {e}")
        return None

    # Player Information
    try:
        players = state_data.get('players', [])
        if len(players) == NUM_PLAYERS:
            for i, player_info in enumerate(players):
                player_offset = current_offset + i * FEATURES_PER_PLAYER
                resources = player_info.get("resources", {})
                for j, res_name in enumerate(RESOURCE_ORDER):
                    count = resources.get(res_name, 0)
                    # Normalize resource count
                    state_vector[player_offset + j] = min(count, MAX_RESOURCES_PER_TYPE) / MAX_RESOURCES_PER_TYPE

                vp = player_info.get("victoryPoints", 0)
                # Normalize victory points
                state_vector[player_offset + NUM_RESOURCES] = min(vp, MAX_VICTORY_POINTS) / MAX_VICTORY_POINTS
        else:
            logging.warning(f"Expected {NUM_PLAYERS} players, found {len(players)}. Skipping player encoding.")
        current_offset += PLAYER_SECTION_SIZE
    except Exception as e:
        logging.exception(f"Error vectorizing players: {e}")
        return None

    # Global Information
    try:
        current_player_idx = state_data.get("currentPlayerIndex", 0)
        state_vector[current_offset + 0] = float(current_player_idx) # Should be 0 or 1

        dice_result = state_data.get("diceResult", 0)
        # Normalize dice roll (2-12 -> 0.0-1.0)
        if isinstance(dice_result, int) and 2 <= dice_result <= 12:
            state_vector[current_offset + 1] = (dice_result - 2.0) / 10.0
        else:
            state_vector[current_offset + 1] = 0.0 # Or some other default for invalid/no roll
        current_offset += GLOBAL_FEATURES_SIZE
    except Exception as e:
        logging.exception(f"Error vectorizing global info: {e}")
        return None

    # Final Check
    if current_offset != TOTAL_VECTOR_SIZE:
         # This indicates a potential mismatch between calculation and implementation
         logging.error(f"Vectorization ended at offset {current_offset}, expected {TOTAL_VECTOR_SIZE}.")
         return None # Vector is likely corrupt or incomplete

    return state_vector

# Example Usage
if __name__ == "__main__":
    print(f"State vector total size: {TOTAL_VECTOR_SIZE}")

    # Dummy state with correct resource names
    dummy_state_example = {
        "gameStateId": "dummy_test_1",
        "currentPlayerIndex": 0,
        "diceResult": 7,
        "hexes": [{"id": i, "resource": random.choice(HEX_RESOURCE_TYPES), "numberToken": random.choice([2,3,4,5,6,8,9,10,11,12, None])} for i in range(NUM_HEXES)],
        "roads": [{"id": i, "ownerPlayerIndex": random.choice([-1, 0, 1])} for i in range(NUM_ROADS)],
        "buildings": [{"id": i, "ownerPlayerIndex": random.choice([-1, 0, 1]), "type": random.choice(BUILDING_TYPES)} for i in range(NUM_INTERSECTIONS)],
        "players": [
            {"index": 0, "resources": {"WOOD": 2, "BRICK": 1, "SHEEP": 0, "WHEAT": 3, "STONE": 0}, "victoryPoints": 3},
            {"index": 1, "resources": {"WOOD": 1, "BRICK": 0, "SHEEP": 4, "WHEAT": 1, "STONE": 2}, "victoryPoints": 4}
        ],
        "availableActions": []
    }

    print("\nTesting vectorization with dummy data:")
    vector = vectorize_state(dummy_state_example)

    if vector is not None:
        print(f"Successfully generated vector of size: {vector.shape}")
        # print(f"Sample (Global Features): {vector[-GLOBAL_FEATURES_SIZE:]}")
    else:
        print("Vectorization failed.")