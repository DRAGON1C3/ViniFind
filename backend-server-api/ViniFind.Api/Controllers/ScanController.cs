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

        public ScanController(ILogger<ScanController> logger, IRabbitMqProducer rabbitMqProducer)
        {
            _logger = logger;
            _rabbitMqProducer = rabbitMqProducer;
        }

        [HttpPost]
        [Consumes("multipart/form-data")]
        public async Task<IActionResult> UploadScan([FromForm] ScanUploadRequest request)
        {
            var file = request.File;

            // Базовая проверка файла
            if (file == null || file.Length == 0)
            {
                return BadRequest(new { error = "Файл изображения не передан или пуст." });
            }

            var taskId = Guid.NewGuid().ToString();

            using var memoryStream = new MemoryStream();
            await file.CopyToAsync(memoryStream);
            var imageBytes = memoryStream.ToArray();

            await _rabbitMqProducer.PublishScanTaskAsync(taskId, file.FileName, imageBytes);

            return Ok(new
            {
                taskId = taskId,
                status = "Queued",
                message = "Задача успешно поставлена в очередь на обработку."
            });
        }
    }
}