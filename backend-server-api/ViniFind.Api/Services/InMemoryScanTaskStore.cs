using System.Collections.Concurrent;
using ViniFind.Api.Models;

namespace ViniFind.Api.Services
{
    public sealed class InMemoryScanTaskStore : IScanTaskStore
    {
        private readonly ConcurrentDictionary<string, ScanTaskState> _tasks = new();
        
        public void Create(string taskId)
        {
            var state = new ScanTaskState
            {
                TaskId = taskId,
                Status = ScanTaskStatus.Queued,
                CreatedAtUtc = DateTime.UtcNow
            };
            
            if (!_tasks.TryAdd(taskId, state))
            {
                throw new InvalidOperationException(
                    $"Задача с ID '{taskId}' уже существует");
            }
        }

        public bool TryGet(string taskId, out ScanTaskState? task)
        {
            return _tasks.TryGetValue(taskId, out task);
        }

        public bool TrySetProcessing(string taskId)
        {
            if (!_tasks.TryGetValue(taskId, out var task))
            {
                return false;
            }

            lock (task)
            {
                if (task.Status != ScanTaskStatus.Queued)
                {
                    return false;
                }

                task.Status = ScanTaskStatus.Processing;
                return true;
            }
            
        }

        public bool TrySetResult(string taskId, ScanResultMessage message)
        {
            if (!_tasks.TryGetValue(taskId, out var task))
            {
                return false;
            }

            lock (task)
            {
                task.Status = message.Status;
                task.Result = message.Result;
                task.Alternatives = message.Alternatives;
                task.Error = message.Error;
                task.CompletedAtUtc = DateTime.UtcNow;
                return true;
            }
        }
    }
}
