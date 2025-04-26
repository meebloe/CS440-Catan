# client_test/test_client.py

import requests
import json
import random

# The URL where your Flask server is running
SERVER_URL = "http://localhost:5000/get_action"

def create_dummy_game_state():
    """Creates a sample Catan game state JSON object."""

    # Define some possible actions for the dummy state
    possible_actions = [
        {"actionType": "BUILD_ROAD", "edgeIndex": random.randint(0, 71)},
        {"actionType": "BUILD_ROAD", "edgeIndex": random.randint(0, 71)},
        {"actionType": "BUILD_SETTLEMENT", "intersectionIndex": random.randint(0, 53)},
        {"actionType": "BUILD_CITY", "intersectionIndex": random.randint(0, 53)},
        {"actionType": "BANK_TRADE_4_1", "resourceOut": random.choice(["WOOL", "BRICK", "LUMBER"]), "resourceIn": random.choice(["GRAIN", "ORE"])},
        {"actionType": "END_TURN"}
    ]

    # Randomly select a subset of actions to be "available"
    available_actions = random.sample(possible_actions, k=random.randint(1, len(possible_actions)))
    # Ensure END_TURN is always an option for simplicity in testing
    if not any(action['actionType'] == 'END_TURN' for action in available_actions):
         available_actions.append({"actionType": "END_TURN"})


    dummy_state = {
        "gameStateId": f"dummy_game_{random.randint(1,100)}_turn_{random.randint(1,50)}",
        "currentPlayerIndex": random.choice([0, 1]),
        "diceResult": randint(2, 12),
        "hexes": [{"id": i, "resource": random.choice(["LUMBER", "WOOL", "GRAIN", "BRICK", "ORE", "DESERT"]), "numberToken": random.choice([2,3,4,5,6,8,9,10,11,12, None])} for i in range(19)],
        "roads": [{"id": i, "ownerPlayerIndex": random.choice([-1, 0, 1])} for i in range(72)],
        "buildings": [{"id": i, "ownerPlayerIndex": random.choice([-1, 0, 1]), "type": random.choice(["NONE", "SETTLEMENT", "CITY"])} for i in range(54)],
        "players": [
            {
                "index": 0,
                "resources": {"LUMBER": random.randint(0,5), "BRICK": random.randint(0,5), "WOOL": random.randint(0,5), "GRAIN": random.randint(0,5), "ORE": random.randint(0,5)},
                "victoryPoints": random.randint(0,10)
            },
            {
                "index": 1,
                "resources": {"LUMBER": random.randint(0,5), "BRICK": random.randint(0,5), "WOOL": random.randint(0,5), "GRAIN": random.randint(0,5), "ORE": random.randint(0,5)},
                "victoryPoints": random.randint(0,10)
            }
        ],
        "availableActions": available_actions
        # "availableActions": [{"actionType": "targetHexIndex": 5, "targetPlayerIndex": 1}]
    }
    return dummy_state

def send_request(state_payload):
    """Sends the state payload to the server and prints the response."""
    headers = {'Content-Type': 'application/json'}
    try:
        print(f"--- Sending State ---")
        print(json.dumps(state_payload, indent=2)) # Print the state being sent

        response = requests.post(SERVER_URL, headers=headers, json=state_payload, timeout=10) # Send data using json parameter

        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        print(f"\n--- Received Response (Status Code: {response.status_code}) ---")
        action_response = response.json()
        print(json.dumps(action_response, indent=2))
        print("-" * 20)
        return action_response

    except requests.exceptions.ConnectionError:
        print(f"\n*** Error: Could not connect to the server at {SERVER_URL}.")
        print("*** Please ensure the Flask server (catan_ai_server.py) is running.")
        print("-" * 20)
    except requests.exceptions.Timeout:
        print(f"\n*** Error: The request to {SERVER_URL} timed out.")
        print("-" * 20)
    except requests.exceptions.RequestException as e:
        print(f"\n*** An error occurred during the request: {e}")
        # If server returned an error (e.g., 500), response might have details
        try:
            print("Server Response Content:", response.text)
        except NameError:
            pass # Response object doesn't exist if connection failed early
        print("-" * 20)
    except Exception as e:
        print(f"\n*** An unexpected error occurred in the client: {e}")
        print("-" * 20)

    return None


if __name__ == "__main__":
    print("Catan AI Test Client")
    print(f"Attempting to send request to: {SERVER_URL}")

    # Create a dummy game state
    dummy_state_data = create_dummy_game_state()

    # Send the request
    received_action = send_request(dummy_state_data)

    if received_action:
        print("\nSuccessfully received an action from the server.")
    else:
        print("\nFailed to receive a valid action from the server.")