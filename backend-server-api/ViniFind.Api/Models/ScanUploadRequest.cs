namespace ViniFind.Api.Models
{
    public class ScanUploadRequest
    {
        public required IFormFile File { get; set; }
    }
}