using Microsoft.AspNetCore.Mvc;
using ViniFind.Api.Models;
using ViniFind.Api.Services;

namespace ViniFind.Api.Controllers;

[ApiController]
[Route("api/jury")]
public sealed class JuryController : ControllerBase
{
    private const long MaxFileSize = 10 * 1024 * 1024;
    private static readonly TimeSpan ProcessingTimeout = TimeSpan.FromSeconds(15);
    private static readonly TimeSpan PollInterval = TimeSpan.FromMilliseconds(100);
    private static readonly HashSet<string> AllowedContentTypes =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "image/jpeg",
            "image/png",
            "image/webp"
        };

    private readonly ILogger<JuryController> _logger;
    private readonly IRabbitMqProducer _rabbitMqProducer;
    private readonly IScanTaskStore _scanTaskStore;

    public JuryController(
        ILogger<JuryController> logger,
        IRabbitMqProducer rabbitMqProducer,
        IScanTaskStore scanTaskStore)
    {
        _logger = logger;
        _rabbitMqProducer = rabbitMqProducer;
        _scanTaskStore = scanTaskStore;
    }

    [HttpPost("scan")]
    [Consumes("multipart/form-data")]
    public async Task<IActionResult> Scan(
        [FromForm] ScanUploadRequest request,
        CancellationToken cancellationToken)
    {
        var file = request.File;

        if (file is null || file.Length == 0)
        {
            return BadRequest(new { error = "Файл изображения не передан или пуст." });
        }

        if (file.Length > MaxFileSize)
        {
            return BadRequest(new { error = "Размер изображения не должен превышать 10 МБ." });
        }

        if (string.IsNullOrWhiteSpace(file.ContentType) ||
            !AllowedContentTypes.Contains(file.ContentType))
        {
            return BadRequest(new
            {
                error = "Поддерживаются только изображения JPEG, PNG и WebP."
            });
        }

        var taskId = Guid.NewGuid().ToString();
        _scanTaskStore.Create(taskId);

        try
        {
            await using var memoryStream = new MemoryStream();
            await file.CopyToAsync(memoryStream, cancellationToken);

            await _rabbitMqProducer.PublishScanTaskAsync(
                taskId,
                file.FileName,
                memoryStream.ToArray());

            var result = await WaitForResultAsync(taskId, cancellationToken);

            if (result is null)
            {
                _scanTaskStore.TrySetFailed(
                    taskId,
                    "Превышено время ожидания результата ML-сервиса.");

                return StatusCode(StatusCodes.Status504GatewayTimeout, new
                {
                    error = "Сервис распознавания не успел обработать изображение."
                });
            }

            if (result.Status == ScanTaskStatus.NotFound ||
                result.Status == ScanTaskStatus.Failed)
            {
                return StatusCode(
                    result.Status == ScanTaskStatus.NotFound
                        ? StatusCodes.Status404NotFound
                        : StatusCodes.Status503ServiceUnavailable,
                    new { error = result.Error ?? "Не удалось распознать вино." });
            }

            var slug = result.Result?.Slug;
            if (result.Status != ScanTaskStatus.Completed ||
                string.IsNullOrWhiteSpace(slug))
            {
                _logger.LogWarning(
                    "ML-сервис вернул неполный результат для jury-задачи {TaskId}.",
                    taskId);

                return StatusCode(
                    StatusCodes.Status502BadGateway,
                    new { error = "ML-сервис вернул некорректный результат." });
            }

            return Ok(new { slug });
        }
        catch (OperationCanceledException)
            when (cancellationToken.IsCancellationRequested)
        {
            _logger.LogWarning(
                "Jury-запрос для задачи {TaskId} был отменён клиентом.",
                taskId);
            throw;
        }
        catch (Exception exception)
        {
            _logger.LogError(
                exception,
                "Не удалось обработать jury-задачу {TaskId}.",
                taskId);

            _scanTaskStore.TrySetFailed(
                taskId,
                "Не удалось поставить изображение в очередь обработки.");

            return StatusCode(
                StatusCodes.Status503ServiceUnavailable,
                new { error = "Сервис обработки временно недоступен." });
        }
    }

    private async Task<ScanTaskState?> WaitForResultAsync(
        string taskId,
        CancellationToken cancellationToken)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(
            cancellationToken);
        timeout.CancelAfter(ProcessingTimeout);

        try
        {
            while (true)
            {
                if (_scanTaskStore.TryGet(taskId, out var task) &&
                    task is not null &&
                    task.Status is ScanTaskStatus.Completed
                        or ScanTaskStatus.NotFound
                        or ScanTaskStatus.Failed)
                {
                    return task;
                }

                await Task.Delay(PollInterval, timeout.Token);
            }
        }
        catch (OperationCanceledException)
            when (!cancellationToken.IsCancellationRequested)
        {
            return null;
        }
    }
}
