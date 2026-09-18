namespace ViniFind.Api.Models
{
    public sealed class ScanTaskState
    {
        public string TaskId { get; set; } = string.Empty;
        public ScanTaskStatus Status { get; set; }
        public WineResult? Result { get; set; }
        public IReadOnlyCollection<WineAlternative> Alternatives { get; set; } = Array.Empty<WineAlternative>();
        public string? Error { get; set; }
        public DateTime CreatedAtUtc { get; set; }
        public DateTime? CompletedAtUtc { get; set; }
    }
}
