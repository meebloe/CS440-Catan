using System;
using System.Collections.Generic;

namespace CatanGameLib
{
    public static class BoardGenerator
    {
        private static readonly int[][] Neighbors = {
            new[] { 1, 3, 4 },         // Hex 0
            new[] { 0, 4, 5, 2 },      // Hex 1
            new[] { 1, 5, 6 },         // Hex 2
            new[] { 0, 4, 7, 8 },      // Hex 3
            new[] { 0, 1, 3, 8, 9, 5 },// Hex 4
            new[] { 1, 2, 4, 9, 10, 6 },// Hex 5
            new[] { 2, 5, 10, 11 },    // Hex 6
            new[] { 3, 8, 12 },        // Hex 7
            new[] { 3, 4, 7, 12, 13, 9 },// Hex 8
            new[] { 4, 5, 8, 13, 14, 10 },// Hex 9
            new[] { 5, 6, 9, 14, 15, 11 },// Hex 10
            new[] { 6, 10, 15 },       // Hex 11
            new[] { 7, 8, 13, 16 },    // Hex 12
            new[] { 8, 9, 12, 16, 17, 14 },// Hex 13
            new[] { 9, 10, 13, 17, 18, 15 },// Hex 14
            new[] { 10, 11, 14, 18 },  // Hex 15
            new[] { 12, 13, 17 },      // Hex 16
            new[] { 13, 14, 16, 18 },  // Hex 17
            new[] { 14, 15, 17 }       // Hex 18
        };

        public static Board GenerateBoard()
        {
            Random rng = new Random();
            Board board = new Board();

            // Define the correct hex distribution
            List<string> hexTypes = new List<string>
            {
                "Stone", "Stone", "Stone",
                "Brick", "Brick", "Brick",
                "Wheat", "Wheat", "Wheat", "Wheat",
                "Wood", "Wood", "Wood", "Wood",
                "Sheep", "Sheep", "Sheep", "Sheep",
                "Desert"
            };

            List<int> numberTokens = new List<int>
            {
                2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12
            };

            // Hardcoded harbor positions
            var harborDefinitions = new List<(int Position, string ResourceType)>
            {
                // **Flats** (0, 5, 10, 15, 20, 25)
                (0, "Brick"),    // Up Left from center
                (5, "Wood"),     // Up Right from center
                (10, "Special"), // Right from center
                (15, "Wheat"),   // Down Right from center
                (20, "Sheep"),   // Down Left from center
                (25, "Ore"),     // Left from center

                // **Group 1** (1/2, 3/4, 16/17, 18/19)
                (1, "Special"),  // Right of 0
                (2, "Special"),  
                (3, "Special"),  // Left of 5
                (4, "Special"),  
                (16, "Special"), // Inverted X of 3/4
                (17, "Special"), 
                (18, "Special"), // Inverted Y of 1/2
                (19, "Special"), 

                // **Group 2** (6/7, 13/14, 21/22, 28/29)
                (6, "Brick"),    // Down Right of 5
                (7, "Wood"),     
                (13, "Special"), // Inverted Y of 6/7
                (14, "Special"), 
                (21, "Special"), // Inverted X/Y of 6/7
                (22, "Special"), 
                (28, "Special"), // Inverted X of 6/7
                (29, "Special"), 

                // **Group 3** (8/9, 11/12, 23/24, 26/27)
                (8, "Brick"),    // Quarter left, Up from 10
                (9, "Wood"),     
                (11, "Special"), // Inverted Y of 8/9
                (12, "Special"), 
                (23, "Special"), // Inverted X/Y of 8/9
                (24, "Special"), 
                (26, "Special"), // Inverted X of 8/9
                (27, "Special")  
            };

            foreach (var (position, resourceType) in harborDefinitions)
            {
                var harbor = new Harbor(position, resourceType);
                board.Harbors.Add(harbor);

            }

            // Shuffle
            hexTypes.Sort((a, b) => rng.Next(-1, 2));
            numberTokens.Sort((a, b) => rng.Next(-1, 2));

            // Create hexes and assign them to positions 0-18
            List<Hex> hexes = new List<Hex>();
            Dictionary<int, int?> placedNumbers = new Dictionary<int, int?>();

            List<int> hexIndexes = new List<int>();
            for (int i = 0; i < hexTypes.Count; i++)
                hexIndexes.Add(i);
            hexIndexes.Sort((a, b) => rng.Next(-1, 2));

            for (int i = 0; i < hexTypes.Count; i++)
            {
                string resource = hexTypes[i];
                int? number = null;

                if (resource != "Desert")
                {
                    // Find a valid number
                    foreach (int candidate in numberTokens)
                    {
                        bool isValid = true;

                        foreach (int neighbor in Neighbors[i])
                        {
                            if (placedNumbers.ContainsKey(neighbor) && (placedNumbers[neighbor] == 6 || placedNumbers[neighbor] == 8) && (candidate == 6 || candidate == 8))
                            {
                                isValid = false;
                                break;
                            }
                        }

                        if (isValid)
                        {
                            number = candidate;
                            numberTokens.Remove(candidate);
                            break;
                        }
                    }
                }

                hexes.Add(new Hex(i, resource, number));
                placedNumbers[i] = number;
            }

            board.Hexes = hexes;

            return board;
        }
    }
}
