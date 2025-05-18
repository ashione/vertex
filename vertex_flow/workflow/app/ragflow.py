import requests
import tempfile
from vertex_flow.workflow.vertex import FunctionVertex
from vertex_flow.workflow.workflow import WorkflowContext
from typing import Dict, Any
from vertex_flow.utils.logger import LoggerUtil
import os

logging = LoggerUtil.get_logger()


class DownloadFileVertex(FunctionVertex):
    def __init__(
        self, id: str, name: str = None, params: Dict[str, Any] = None, variables=None
    ):
        super().__init__(
            id=id,
            name=name,
            task=self.download_file,
            params=params,
            variables=variables,
        )

    def _delete_tmp_file(self):
        if not hasattr(self, "tmpfile_path"):
            return
        if os.path.exists(self.tmpfile_path):
            logging.info(f"remove {self.tmpfile_path}")
            os.remove(self.tmpfile_path)
        else:
            logging.info(f"{self.tmpfile_path} not exists")

    def on_workflow_finished(self):
        self._delete_tmp_file()

    def on_workflow_failed(self):
        self._delete_tmp_file()

    def download_file(
        self, inputs: Dict[str, Any], context: WorkflowContext[Any] = None
    ):
        local_inputs = self.resolve_dependencies(inputs=inputs)
        url = local_inputs.get("url")
        if not url:
            raise ValueError("URL is required for downloading the file.")

        self.tmpfile_path = inputs.get("tmpfile_path")
        if not self.tmpfile_path:
            # 如果没有指定临时文件路径，则创建一个临时文件
            tmpfile = tempfile.NamedTemporaryFile(delete=False)
            self.tmpfile_path = tmpfile.name
            tmpfile.close()

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # 检查请求是否成功

            with open(self.tmpfile_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logging.info(f"File downloaded and saved to {self.tmpfile_path}")
            return {"tmpfile_path": self.tmpfile_path, "status": "success"}
        except Exception as e:
            logging.error(f"Error downloading file from {url}: {e}")
            self.output = {"status": "error", "message": str(e)}
            raise e
