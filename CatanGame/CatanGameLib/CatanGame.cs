using System.Collections.Generic;

namespace CatanGameLib;

public class CatanGame
{
    public Board Board { get; private set; }
    public List<Player> Players { get; private set; }

    public CatanGame()
    {
        Players = new List<Player>
        {
            new Player("Red"),
            new Player("Blue"),
            new Player("White"),
            new Player("Orange")
        };
    }

    public void Start()
    {
        Board = BoardGenerator.GenerateBoard();
    }
}
