using System.Collections.Generic;

namespace CatanGameLib;

public class GameController
{
    public Board Board { get; private set; }
    public List<Player> Players { get; private set; }

    public GameController()
    {
        Players = new List<Player>
        {
            new Player("Red"),
            new Player("Blue"),
            new Player("White"),
            new Player("Orange")
        };

        Board = BoardGenerator.GenerateBoard();
    }

    public List<Hex> GetHexes()
    {
        return Board?.Hexes ?? new List<Hex>();
    }

    public List<Harbor> GetHarbors()
    {
        return Board?.Harbors ?? new List<Harbor>();
    }
}
