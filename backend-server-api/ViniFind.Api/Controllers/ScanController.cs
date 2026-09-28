using Microsoft.AspNetCore.Mvc;
using ViniFind.Api.Models;
using ViniFind.Api.Services;

namespace ViniFind.Api.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class ScanController : ControllerBase
    {
        private readonly ILogger<ScanController> _logger;
        private readonly IRabbitMqProducer _rabbitMqProducer;
        private readonly IScanTaskStore _scanTaskStore;
        public ScanController(ILogger<ScanController> logger, IRabbitMqProducer rabbitMqProducer, IScanTaskStore scanTaskStore)
        {
            _logger = logger;
            _rabbitMqProducer = rabbitMqProducer;
            _scanTaskStore = scanTaskStore;
        }

        [HttpPost]
        [Consumes("multipart/form-data")]
        public async Task<IActionResult> UploadScan(
            [FromForm] ScanUploadRequest request,
            CancellationToken cancellationToken)
                {
                    const long maxFileSize = 10 * 1024 * 1024; // 10 MB

                    var allowedContentTypes = new HashSet<string>(
                        StringComparer.OrdinalIgnoreCase)
                    {
                        "image/jpeg",
                        "image/png",
                        "image/webp"
                    };

                var file = request.File;

                // Ошибки валидации не создают задачу и не требуют статуса Failed.
                if (file is null || file.Length == 0)
                {
                    return BadRequest(new
                    {
                        error = "Файл изображения не передан или пуст."
                    });
                }

                if (file.Length > maxFileSize)
                {
                    return BadRequest(new
                    {
                        error = "Размер изображения не должен превышать 10 МБ."
                    });
                }

                if (string.IsNullOrWhiteSpace(file.ContentType) ||
                    !allowedContentTypes.Contains(file.ContentType))
                {
                    return BadRequest(new
                    {
                        error = "Поддерживаются только изображения JPEG, PNG и WebP."
                    });
                }

                var taskId = Guid.NewGuid().ToString();

                // Регистрируем задачу только после успешной валидации файла.
                _scanTaskStore.Create(taskId);

                try
                {
                    await using var memoryStream = new MemoryStream();

                    await file.CopyToAsync(
                        memoryStream,
                        cancellationToken);

                    var imageBytes = memoryStream.ToArray();

                    await _rabbitMqProducer.PublishScanTaskAsync(
                        taskId,
                        file.FileName,
                        imageBytes);

                    return Ok(new
                    {
                        taskId,
                        status = ScanTaskStatus.Queued,
                        message = "Задача успешно поставлена в очередь на обработку."
                    });
                }
                catch (OperationCanceledException)
                    when (cancellationToken.IsCancellationRequested)
                {
                    _logger.LogWarning(
                        "Запрос на обработку задачи {TaskId} был отменён клиентом.",
                        taskId);

                    // Отмену запроса не нужно превращать в ошибку RabbitMQ.
                    throw;
                }
                catch (Exception exception)
                {
                    _logger.LogError(
                        exception,
                        "Не удалось поставить задачу {TaskId} в RabbitMQ.",
                        taskId);

                    _scanTaskStore.TrySetFailed(
                        taskId,
                        "Не удалось поставить изображение в очередь обработки.");

                    return StatusCode(
                        StatusCodes.Status503ServiceUnavailable,
                        new
                        {
                            taskId,
                            status = ScanTaskStatus.Failed,
                            error = "Сервис обработки временно недоступен."
                        });
                }
            }

        [HttpGet("{taskId}")]
        public IActionResult GetScanStatus(string taskId)
        {
            if (!_scanTaskStore.TryGet(taskId, out var task) || task is null)
            {
                return NotFound(new
                {
                    taskId,
                    error = "Задача не найдена."
                });
            }

            return Ok(task);
        }
    }
}