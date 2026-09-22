using Microsoft.Extensions.Hosting;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using System.IO.Pipes;
using System.Text.Json;
using System.Text.Json.Serialization;
using ViniFind.Api.Models;
using ViniFind.Api.Services;

namespace ViniFind.Api.Service;

public sealed class RabbitMqResultConsumer : BackgroundService
{
    private readonly IConfiguration _configuration;
    private readonly IScanTaskStore _taskStore;
    private readonly ILogger<RabbitMqResultConsumer> _logger;
    public RabbitMqResultConsumer(
        IConfiguration configuration,
        IScanTaskStore taskStore,
        ILogger<RabbitMqResultConsumer> logger)
    {
        _configuration = configuration;
        _taskStore = taskStore;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(
        CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await RunConsumerSessionAsync(stoppingToken);
            }
            catch (OperationCanceledException)
                when (stoppingToken.IsCancellationRequested)
            {
                _logger.LogInformation(
                     "Остановка консьюмера RabbitMQ.");
            }
            catch (Exception exception)
            {
                _logger.LogError(
                    exception,
                    "Ошибка в консьюмере RabbitMQ. Перезапуск через 5 секунд.");
            }

            if (!stoppingToken.IsCancellationRequested)
            {
                try
                {
                    await Task.Delay(
                        TimeSpan.FromSeconds(5),
                        stoppingToken);
                }
                catch (OperationCanceledException)
                    when (stoppingToken.IsCancellationRequested)
                {
                    _logger.LogInformation(
                        "Ожидание переподключения отменено.");
                }
            }
        }
    }

    private async Task RunConsumerSessionAsync(
        CancellationToken stoppingToken)
    {
        var rabbitMqSection = _configuration.GetSection("RabbitMQ");

        var host = rabbitMqSection["Host"] ?? "localhost";

        var username = rabbitMqSection["Username"] ?? "guest";

        var password = rabbitMqSection["Password"] ?? "guest";

        var queueName = rabbitMqSection["ResultQueueName"] ?? "wine_scan_results";

        if (!int.TryParse(
            rabbitMqSection["Port"],
            out var port))
        {
            port = 5672;
        }

        var factory = new ConnectionFactory
        {
            HostName = host,
            Port = port,
            UserName = username,
            Password = password
        };

        await using var connection = await factory.CreateConnectionAsync(stoppingToken);
        await using var channel = await connection.CreateChannelAsync(cancellationToken: stoppingToken);
        await channel.QueueDeclareAsync(
            queue: queueName,
            durable: true,
            exclusive: false,
            autoDelete: false,
            arguments: null,
            cancellationToken: stoppingToken);
        await channel.BasicQosAsync(
            prefetchSize: 0,
            prefetchCount: 1,
            global: false,
            cancellationToken: stoppingToken);
        var consumer = new AsyncEventingBasicConsumer(channel);
        consumer.ReceivedAsync += async (_, EventArgs) =>
        {
            await ProcessMessageAsync(channel, EventArgs);
        };

        await channel.BasicConsumeAsync(
            queue: queueName,
            autoAck: false,
            consumer: consumer,
            cancellationToken: stoppingToken);

        _logger.LogInformation(
            "RabbitMQ consumer слушает очередь {QueueName}.",
            queueName);

        var connectionClosed = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);

        connection.ConnectionShutdownAsync += (_, _) =>
        {
            connectionClosed.TrySetResult(true);
            return Task.CompletedTask;
        };

        await Task.WhenAny(
            connectionClosed.Task,
            Task.Delay(Timeout.InfiniteTimeSpan, stoppingToken));

        stoppingToken.ThrowIfCancellationRequested();
        throw new InvalidOperationException(
            "Соедение с RabbitMQ было закрыто.");
    }

    private async Task ProcessMessageAsync(
        IChannel channel,
        BasicDeliverEventArgs eventArgs)
    {
        try
        {
            var message = JsonSerializer.Deserialize<ScanResultMessage>(
                eventArgs.Body.Span,
                new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true,
                    Converters =
                    {
                        new JsonStringEnumConverter()
                    }
                });

            if (message is null || string.IsNullOrWhiteSpace(message.TaskId))
            {
                _logger.LogWarning(
                    "Получено некорректное сообщение без TaskId.");

                await channel.BasicAckAsync(
                    deliveryTag: eventArgs.DeliveryTag,
                    multiple: false);

                return;
            }

            var updated = _taskStore.TrySetResult(
                message.TaskId,
                message);

            if (!updated)
            {
                _logger.LogWarning(
                    "Результат получен для неизвестной задачи {TaskId}.",
                    message.TaskId);
            }
            else
            {
                _logger.LogInformation(
                    "Результат для задачи {TaskId} сохранён со статусом {Status}.",
                    message.TaskId,
                    message.Status);
            }

            await channel.BasicAckAsync(
                deliveryTag: eventArgs.DeliveryTag,
                multiple: false);
        }
        catch (JsonException exception)
        {
            _logger.LogError(
                exception,
                "Не удалось десериализовать сообщение RabbitMQ.");

            // Сообщение без корректного JSON бессмысленно повторять.
            await channel.BasicNackAsync(
                deliveryTag: eventArgs.DeliveryTag,
                multiple: false,
                requeue: false);
        }
        catch (Exception exception)
        {
            _logger.LogError(
                exception,
                "Ошибка обработки результата RabbitMQ.");

            // Временную ошибку возвращаем в очередь для повторной обработки.
            await channel.BasicNackAsync(
                deliveryTag: eventArgs.DeliveryTag,
                multiple: false,
                requeue: true);
        }
    }
}
