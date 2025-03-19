using System.Collections.Generic;

namespace CatanGameLib;

public class Board
{
    public List<Hex> Hexes { get; set; }
    public List<Intersection> Intersections { get; set; }
    public List<Edge> Edges { get; set; }

    public Board()
    {
        Hexes = new List<Hex>();
        Intersections = new List<Intersection>();
        Edges = new List<Edge>();
    }
}
