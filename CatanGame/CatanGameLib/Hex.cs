using System.Collections.Generic;

namespace CatanGameLib;

public class Hex
{
    public int Id { get; set; }
    public string Resource { get; set; }
    public int? Number { get; set; }
    public List<Intersection> Intersections { get; set; }

    public Hex(int id, string resource, int? number)
    {
        Id = id;
        Resource = resource;
        Number = number;
        Intersections = new List<Intersection>();
    }
}
