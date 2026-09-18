namespace ViniFind.Api.Models
{
    public sealed class ScanResultMessage
    {
        public string TaskId { get; set; } = string.Empty;
        public ScanTaskStatus Status { get; set; }
        public WineResult? Result { get; set; }
        public IReadOnlyCollection<WineAlternative> Alternatives { get; init; } = Array.Empty<WineAlternative>();
        public string? Error { get; set; }
    }
}
