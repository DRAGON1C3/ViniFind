namespace ViniFind.Api.Models
{
    public sealed class WineResult
    {
        public string Slug { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public int? Rating { get; set; }
        public int? Year { get; set; }
        public string? Country { get; set; }
        public string? Region { get; set; }
        public string? Fact { get; set; }
        public double? Confidence { get; set; }
        public IReadOnlyCollection<WineAlternative> Alternatives { get; init; } = Array.Empty<WineAlternative>();
    }

    public sealed class WineAlternative
    {
        public string Slug { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
    }
}
