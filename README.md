# Catan AI Project (Unity <-> Python Communication PoC)

## Overview

This project aims to develop an AI agent capable of playing a simplified version of the board game Settlers of Catan. The current focus is establishing a communication Proof-of-Concept (PoC) between a game engine (intended to be Unity) and a Python-based AI server using a REST API (Flask).

The setup involves:

1.  **Python Flask Server (`server/catan_ai_server.py`):** Listens for HTTP POST requests containing the current game state in JSON format. It processes the state, determines a valid action (currently, randomly selects from provided options), and returns the chosen action as JSON.
2.  **Game Client (Unity / `client_test/test_client.py`):** Responsible for running the game logic, determining legal moves, serializing the game state to JSON, sending it to the Python server, receiving the chosen action JSON, and executing that action. This repository includes a Python test client (`test_client.py`) to simulate sending requests for testing purposes.

This README focuses on setting up and running the Python server and test client.

## Prerequisites

*   **Conda:** For Python environment management. Download and install Anaconda or Miniconda if you haven't already.
*   **Python:** Recommended version 3.8+ (the environment creation command below uses 3.9, adjust if needed).

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd catan_ai_project
    ```

2.  **Create Conda Environment:**
    Open your terminal or Anaconda Prompt.
    ```bash
    conda create --name catan_ai_env python=3.9
    ```
    *(Replace `catan_ai_env` with your preferred name if desired)*

3.  **Activate Conda Environment:**
    ```bash
    conda activate catan_ai_env
    ```
    *(Your terminal prompt should change to show `(catan_ai_env)`)*

4.  **Install Dependencies:**
    While the environment is active, install the required Python packages:
    ```bash
    conda install flask requests
    ```

## How to Run

You need two terminals open, both with the `catan_ai_env` conda environment activated.

1.  **Run the Flask Server:**
    *   In the first terminal (with `catan_ai_env` active):
    *   Navigate to the server directory: `cd server`
    *   Start the server: `python catan_ai_server.py`
    *   You should see output like `* Running on http://0.0.0.0:5000/` (or similar). The server is now listening for requests. Leave this terminal running.

2.  **Run the Test Client:**
    *   In the second terminal (with `catan_ai_env` active):
    *   Navigate to the test client directory: `cd client_test` (assuming you started from the project root)
    *   Run the test script: `python test_client.py`
    *   The client will:
        *   Generate a sample game state JSON.
        *   Print the JSON it's about to send.
        *   Send the JSON to the running server via an HTTP POST request.
        *   Print the JSON action response received from the server.
    *   You should also see log output in the server terminal indicating it received a request and sent a response.

## JSON Communication Format

Communication between the game client (Unity/Test Client) and the AI server (Python Flask) uses JSON objects sent over HTTP.

### 1. State JSON (Sent from Game Client to AI Server)

This JSON object represents the complete snapshot of the game state needed for the AI to make a decision.

**Structure:**

```javascript
{
  "gameStateId": "string (optional)", // Unique identifier for the state (for logging/debugging)
  "currentPlayerIndex": integer,      // Index (0 or 1) of the player whose turn it is
  "diceRolled": boolean,              // True if dice have been rolled this turn, False otherwise
  "diceResult": [integer, integer] | null, // Array [die1, die2] if rolled, null otherwise
  "mustMoveRobber": boolean,          // True if a 7 was rolled and robber action is mandatory
  "robberHexIndex": integer,          // Index (0-18) of the hex where the robber is currently placed
  "hexes": [                          // List of 19 hex objects (MUST be in consistent order)
    {
      "id": integer,                  // Hex index (0-18)
      "resource": "string" | null,    // Resource type ("LUMBER", "BRICK", "WOOL", "GRAIN", "ORE", "DESERT") or null
      "numberToken": integer | null   // Dice number (2-12, excluding 7) or null (for desert)
    },
    // ... 18 more hex objects
  ],
  "roads": [                          // List of 72 potential road edge objects (MUST be in consistent order)
    {
      "id": integer,                  // Edge index (0-71)
      "ownerPlayerIndex": integer     // Owning player index (0 or 1), or -1 if unoccupied
    },
    // ... 71 more road objects
  ],
  "buildings": [                      // List of 54 potential building intersection objects (MUST be in consistent order)
    {
      "id": integer,                  // Intersection index (0-53)
      "ownerPlayerIndex": integer,    // Owning player index (0 or 1), or -1 if unoccupied
      "type": "string"                // Type of building ("NONE", "SETTLEMENT", "CITY")
    },
    // ... 53 more building objects
  ],
  "players": [                        // List of 2 player objects
    {
      "index": integer,               // Player index (0 or 1)
      "resources": {                  // Dictionary of resource counts
        "LUMBER": integer,
        "BRICK": integer,
        "WOOL": integer,
        "GRAIN": integer,
        "ORE": integer
      },
      "victoryPoints": integer        // Current public victory point count
    },
    { // Player 1 object structure is identical
      "index": 1,
      "resources": { /* ... */ },
      "victoryPoints": integer
    }
  ],
  "availableActions": [               // *** CRITICAL LIST *** of all LEGAL actions the current player can take NOW
    // Each object in this list represents one possible, valid action.
    // Format depends on action type:
    {"actionType": "BUILD_ROAD", "edgeIndex": integer},
    {"actionType": "BUILD_SETTLEMENT", "intersectionIndex": integer},
    {"actionType": "BUILD_CITY", "intersectionIndex": integer}, // Index of the settlement to upgrade
    {"actionType": "BANK_TRADE_4_1", "resourceOut": "string", "resourceIn": "string"}, // Resource names
    {"actionType": "MOVE_ROBBER", "targetHexIndex": integer, "targetPlayerIndex": integer | null}, // Player index to steal from (null if none)
    {"actionType": "END_TURN"}
    // ... potentially other actions if features are added
  ]
}
