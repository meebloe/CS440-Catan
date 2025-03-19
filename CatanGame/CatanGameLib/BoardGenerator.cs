using System;
using System.Collections.Generic;

namespace CatanGameLib;

public static class BoardGenerator
{
    public static Board GenerateBoard()
    {
        Board board = new Board();

        // Manually assign hexes for testing
        board.Hexes = new List<Hex>
        {
            new Hex(0, "Wood", 8),
            new Hex(1, "Sheep", 4),
            new Hex(2, "Brick", 11),
            new Hex(3, "Wheat", 3),
            new Hex(4, "Stone", 9),
            new Hex(5, "Wood", 6),
            new Hex(6, "Sheep", 5),
            new Hex(7, "Wheat", 10),
            new Hex(8, "Stone", 8),
            new Hex(9, "Brick", 6),
            new Hex(10, "Desert", null),
            new Hex(11, "Sheep", 5),
            new Hex(12, "Wheat", 10),
            new Hex(13, "Brick", 9),
            new Hex(14, "Stone", 12),
            new Hex(15, "Wood", 2),
            new Hex(16, "Sheep", 4),
            new Hex(17, "Wheat", 11),
            new Hex(18, "Wood", 3)
        };

        return board;
    }
}