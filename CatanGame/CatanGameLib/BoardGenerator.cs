using System;
using System.Collections.Generic;
using System.Linq;

namespace CatanGameLib
{
    public static class BoardGenerator
    {
        private const int TotalPositions = 30;
        private const int RequiredHarbors = 9;

        public static Board GenerateBoard()
        {
            Random rng = new Random();
            Board board = new Board();

            // Define hex distribution
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

            // Generate dynamic harbor placements
            List<int> harborPositions = GenerateHarborPositions(rng);

            // Define harbor resource types
            List<string> harborResources = new List<string>
            {
                "Brick", "Wood", "Wheat", "Sheep", "Stone",
                "Special", "Special", "Special", "Special"
            };

            // Shuffle harbor resources
            harborResources = harborResources.OrderBy(x => rng.Next()).ToList();

            // Assign harbors to the board
            for (int i = 0; i < RequiredHarbors; i++)
            {
                var harbor = new Harbor(harborPositions[i], harborResources[i]);
                board.Harbors.Add(harbor);
            }

            // Shuffle hex types and number tokens
            hexTypes = hexTypes.OrderBy(x => rng.Next()).ToList();
            numberTokens = numberTokens.OrderBy(x => rng.Next()).ToList();

            // Create hexes and assign them to positions 0-18
            List<Hex> hexes = new List<Hex>();
            Dictionary<int, int?> placedNumbers = new Dictionary<int, int?>();

            for (int i = 0; i < hexTypes.Count; i++)
            {
                string resource = hexTypes[i];
                int? number = null;

                if (resource != "Desert")
                {
                    foreach (int candidate in numberTokens)
                    {
                        bool isValid = true;

                        foreach (int neighbor in Neighbors[i])
                        {
                            if (placedNumbers.ContainsKey(neighbor) &&
                                (placedNumbers[neighbor] == 6 || placedNumbers[neighbor] == 8) &&
                                (candidate == 6 || candidate == 8))
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

        private static List<int> GenerateHarborPositions(Random rng)
        {
            // 6 gaps of size 3 and 2 gaps of size 4
            List<int> gapSizes = new List<int> { 3, 3, 3, 3, 3, 3, 4, 4 };
            gapSizes = gapSizes.OrderBy(x => rng.Next()).ToList(); // Shuffle gaps

            int currentPosition = rng.Next(TotalPositions); // Random start position
            List<int> harborPositions = new List<int> { currentPosition };

            // Generate positions by adding gap sizes
            foreach (int gap in gapSizes)
            {
                currentPosition = (currentPosition + gap) % TotalPositions; // Ensure wrap-around
                harborPositions.Add(currentPosition);
            }

            return harborPositions.OrderBy(x => x).ToList();
        }

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
    }
}
