#nullable enable
using System.Collections.Generic;

namespace CatanGameLib;

public class Intersection
{
    public int Id { get; set; }
    public List<Hex> AdjacentHexes { get; set; }
    public List<Edge> ConnectedEdges { get; set; }
    public Player? Owner { get; set; }
    public Harbor? Harbor { get; set; }

    public Intersection(int id)
    {
        Id = id;
        AdjacentHexes = new List<Hex>();
        ConnectedEdges = new List<Edge>();
        Owner = null;
        Harbor = null;
    }
}
