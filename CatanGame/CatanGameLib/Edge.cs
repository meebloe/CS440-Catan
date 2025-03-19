#nullable enable
using System.Collections.Generic;

namespace CatanGameLib;

public class Edge
{
    public int Id { get; set; }
    public Intersection Start { get; set; }
    public Intersection End { get; set; }
    public Player? Owner { get; set; }

    public Edge(int id, Intersection start, Intersection end)
    {
        Id = id;
        Start = start;
        End = end;
        Owner = null;
    }
}
