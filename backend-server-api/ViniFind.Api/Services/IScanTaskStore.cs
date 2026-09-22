using ViniFind.Api.Models;

namespace ViniFind.Api.Services
{
    public interface IScanTaskStore
    {
        void Create(string taskId);
        bool TryGet(string taskId, out ScanTaskState? state);
        bool TrySetProcessing(string taskId);
        bool TrySetResult(string taskId, ScanResultMessage result);
        bool TrySetFailed(string taskId, string error);

    }
}
