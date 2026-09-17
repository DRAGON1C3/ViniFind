namespace ViniFind.Api.Services
{
    public interface IRabbitMqProducer
    {
        Task PublishScanTaskAsync(string taskId, string fileName, byte[] imageBytes);
    }
}
