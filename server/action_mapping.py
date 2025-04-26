# server/action_mapping.py
import logging
import logging
from typing import Optional

# --- Constants from game rules ---
NUM_ROADS = 72
NUM_INTERSECTIONS = 54
RESOURCE_ORDER = ["LUMBER", "BRICK", "WOOL", "GRAIN", "ORE"] # Must match encoder
NUM_RESOURCES = len(RESOURCE_ORDER)
NUM_HEXES = 19
NUM_PLAYERS = 2 # Specific to 2-player setup

# --- Define Action Categories and Calculate Sizes ---
# NOTE: Make sure these match exactly how actions are represented in availableActions JSON

# 1. Build Road Actions
BUILD_ROAD_ACTIONS_START = 0
BUILD_ROAD_ACTIONS_END = BUILD_ROAD_ACTIONS_START + NUM_ROADS # 0 to 71

# 2. Build Settlement Actions
BUILD_SETTLEMENT_ACTIONS_START = BUILD_ROAD_ACTIONS_END
BUILD_SETTLEMENT_ACTIONS_END = BUILD_SETTLEMENT_ACTIONS_START + NUM_INTERSECTIONS # 72 to 125

# 3. Build City Actions
BUILD_CITY_ACTIONS_START = BUILD_SETTLEMENT_ACTIONS_END
BUILD_CITY_ACTIONS_END = BUILD_CITY_ACTIONS_START + NUM_INTERSECTIONS # 126 to 179

# 4. Bank Trade (4:1) Actions
# We need to map (resource_out, resource_in) pairs to indices
BANK_TRADE_ACTIONS_START = BUILD_CITY_ACTIONS_END
BANK_TRADE_MAPPING = {}
current_trade_index = BANK_TRADE_ACTIONS_START
for i, res_out in enumerate(RESOURCE_ORDER):
    for j, res_in in enumerate(RESOURCE_ORDER):
        if i != j: # Cannot trade for the same resource
            BANK_TRADE_MAPPING[(res_out, res_in)] = current_trade_index
            current_trade_index += 1
BANK_TRADE_ACTIONS_END = current_trade_index # 180 to 199 (5*4 = 20 trades)

# 5. End Turn Action
END_TURN_ACTION_START = BANK_TRADE_ACTIONS_END
END_TURN_ACTION_INDEX = END_TURN_ACTION_START # 201
END_TURN_ACTION_END = END_TURN_ACTION_START + 1

# --- Total Number of Actions ---
TOTAL_ACTIONS = END_TURN_ACTION_END
logging.info(f"Total number of theoretical actions defined: {TOTAL_ACTIONS}") # Should be 201


# --- Function to get action index from action object ---
def get_action_index(action_dict: dict) -> Optional[int]:
    """Maps an action dictionary (from availableActions) to its global index."""
    action_type = action_dict.get("actionType")

    if action_type == "BUILD_ROAD":
        idx = action_dict.get("edgeIndex")
        if idx is not None and 0 <= idx < NUM_ROADS:
            return BUILD_ROAD_ACTIONS_START + idx
    elif action_type == "BUILD_SETTLEMENT":
        idx = action_dict.get("intersectionIndex")
        if idx is not None and 0 <= idx < NUM_INTERSECTIONS:
            return BUILD_SETTLEMENT_ACTIONS_START + idx
    elif action_type == "BUILD_CITY":
        idx = action_dict.get("intersectionIndex")
        if idx is not None and 0 <= idx < NUM_INTERSECTIONS:
            return BUILD_CITY_ACTIONS_START + idx
    elif action_type == "BANK_TRADE_4_1":
        res_out = action_dict.get("resourceOut")
        res_in = action_dict.get("resourceIn")
        if res_out and res_in and (res_out, res_in) in BANK_TRADE_MAPPING:
            return BANK_TRADE_MAPPING[(res_out, res_in)]
    elif action_type == "END_TURN":
        return END_TURN_ACTION_INDEX

    logging.warning(f"Could not map action to index: {action_dict}")
    return None

# --- Example Usage (for testing this file directly) ---
if __name__ == "__main__":
    test_actions = [
        {"actionType": "BUILD_ROAD", "edgeIndex": 5},
        {"actionType": "BUILD_SETTLEMENT", "intersectionIndex": 10},
        {"actionType": "BUILD_CITY", "intersectionIndex": 10},
        {"actionType": "BANK_TRADE_4_1", "resourceOut": "WOOL", "resourceIn": "BRICK"},
        {"actionType": "END_TURN"},
        {"actionType": "INVALID_ACTION"},
        {"actionType": "BUILD_ROAD", "edgeIndex": 99}, # Invalid index
    ]
    print(f"Total Actions: {TOTAL_ACTIONS}")
    for action in test_actions:
        index = get_action_index(action)
        print(f"Action: {action} -> Index: {index}")