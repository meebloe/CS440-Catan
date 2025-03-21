namespace CatanGameLib;

public class Harbor
{
    public string ResourceType { get; set; }
    public int Position { get; set; }

    public Harbor(int position, string resourceType = null)
    {
        Position = position;
        ResourceType = resourceType;
    }
}
