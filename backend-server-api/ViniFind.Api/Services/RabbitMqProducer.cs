using System.Text.Json;
using RabbitMQ.Client;

namespace ViniFind.Api.Services
{
    public class RabbitMqProducer : IRabbitMqProducer
    {
        private readonly IConfiguration _configuration;
        private readonly ILogger<RabbitMqProducer> _logger;
        public RabbitMqProducer(IConfiguration configuration, ILogger<RabbitMqProducer> logger)
        {
            _configuration = configuration;
            _logger = logger;
        }
        public async Task PublishScanTaskAsync(string taskId, string fileName, byte[] imageBytes)
        {
            var rabbitMqSection = _configuration.GetSection("RabbitMq");

            var host = rabbitMqSection["Host"] ?? "localhost";
            var queueName = rabbitMqSection["QueueName"] ?? "wine_scan_tasks";
            var username = rabbitMqSection["Username"] ?? "guest";
            var password = rabbitMqSection["Password"] ?? "guest";

            if (!int.TryParse(rabbitMqSection["Port"], out var port))
            {
                port = 5672; // Default RabbitMQ port
            }

            var factory = new ConnectionFactory
            {
                HostName = host,
                Port = port,
                UserName = username,
                Password = password
            };

            using var connection = await factory.CreateConnectionAsync();
            using var channel = await connection.CreateChannelAsync();

            //Создаем очередь, если она не существует
            await channel.QueueDeclareAsync(queue: queueName,
                                 durable: true,
                                 exclusive: false,
                                 autoDelete: false,
                                 arguments: null);

            var payload = new
            {
                TaskId = taskId,
                FileName = fileName,
                CreatedAt = DateTime.UtcNow,
                ImageBase64 = Convert.ToBase64String(imageBytes)
            };

            var body = JsonSerializer.SerializeToUtf8Bytes(payload);
            var props = new BasicProperties { Persistent = true, ContentType = "application/json" };

            //Отправляем
            await channel.BasicPublishAsync(exchange: string.Empty,
                                 routingKey: queueName,
                                 mandatory: true,
                                 basicProperties: props,
                                 body: body);
            _logger.LogInformation("Сообщение с TaskId {TaskId} отправлено в очередь {QueueName}", taskId, queueName);
        }
    }
}