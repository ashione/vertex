import os
import sys
import time

import yaml
from flask import Flask, jsonify, render_template, request

# 设置CONFIG_PATH环境变量
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))
os.environ["CONFIG_PATH"] = config_path

# 添加vertex_flow到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from vertex_flow.workflow.service import VertexFlowService
from vertex_flow.workflow.workflow import Workflow
from vertex_flow.workflow.workflow_manager import WorkflowManager

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"

# 初始化 VertexFlowService 实例
vertex_service = VertexFlowService()

# 初始化工作流管理器，传入 vertex_service
workflow_manager = WorkflowManager(vertex_service=vertex_service)


@app.route("/")
def index():
    """主页 - 工作流列表"""
    return render_template("index.html")


@app.route("/workflow")
def workflow_editor():
    """工作流编辑器"""
    return render_template("workflow.html")


@app.route("/config")
def config_page():
    """配置页面"""
    return render_template("config.html")


# API路由
@app.route("/api/workflows", methods=["GET"])
def get_workflows():
    """获取所有工作流"""
    try:
        workflows = workflow_manager.get_all_workflows()  # 修改这里

        # 移除不可序列化的workflow_obj
        clean_workflows = []
        for workflow in workflows:
            if workflow and "workflow_obj" in workflow:
                workflow_copy = workflow.copy()
                del workflow_copy["workflow_obj"]
                clean_workflows.append(workflow_copy)
            else:
                clean_workflows.append(workflow)

        return jsonify({"success": True, "data": clean_workflows})
    except Exception as e:
        import traceback

        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/workflows", methods=["POST"])
def create_workflow():
    """创建新工作流"""
    try:
        data = request.json
        workflow_data = workflow_manager.create_workflow(
            name=data.get("name"),
            description=data.get("description", ""),
            # 移除不支持的参数：config, edges 等
        )
        return jsonify({"success": True, "data": workflow_data})
    except Exception as e:
        import traceback

        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/workflows/<workflow_id>", methods=["GET"])
def get_workflow(workflow_id):
    """获取特定工作流"""
    try:
        workflow = workflow_manager.get_workflow(workflow_id)

        # 移除不可序列化的workflow_obj
        if workflow and "workflow_obj" in workflow:
            workflow_copy = workflow.copy()
            del workflow_copy["workflow_obj"]
            workflow = workflow_copy

        return jsonify({"success": True, "data": workflow if workflow else None})
    except Exception as e:
        import traceback

        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/workflows/<workflow_id>", methods=["PUT"])
def update_workflow(workflow_id):
    """更新工作流"""
    try:
        data = request.json
        result = workflow_manager.update_workflow(
            workflow_id,
            name=data.get("name"),
            description=data.get("description"),
            nodes=data.get("nodes"),
            edges=data.get("edges"),
        )

        # 移除不可序列化的workflow_obj
        if result and "workflow_obj" in result:
            result_copy = result.copy()
            del result_copy["workflow_obj"]
            result = result_copy

        return jsonify({"success": result is not None, "data": result})
    except Exception as e:
        import traceback

        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/workflows/<workflow_id>/execute", methods=["POST"])
def execute_workflow(workflow_id):
    """执行工作流 - 返回实例信息"""
    try:
        data = request.json
        input_data = data.get("input", {})

        result = workflow_manager.execute_workflow(workflow_id, input_data)

        return jsonify({"success": result.get("status") != "failed", "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/workflows/<workflow_id>/history", methods=["GET"])
def get_workflow_history(workflow_id):
    """获取工作流执行历史"""
    try:
        history = workflow_manager.get_execution_history(workflow_id)
        return jsonify({"success": True, "data": history})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/workflow-instances/<instance_id>", methods=["GET"])
def get_workflow_instance(instance_id):
    """获取特定工作流实例的详细信息"""
    try:
        instance = workflow_manager.get_workflow_instance(instance_id)
        if not instance:
            return jsonify({"success": False, "error": "Instance not found"}), 404

        return jsonify(
            {
                "success": True,
                "data": {
                    "id": instance.id,
                    "workflow_template_id": instance.workflow_template_id,
                    "status": instance.status,
                    "input_data": instance.input_data,
                    "output_data": instance.output_data,
                    "node_outputs": instance.node_outputs,
                    "created_at": instance.created_at.isoformat(),
                    "started_at": instance.started_at.isoformat() if instance.started_at else None,
                    "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
                    "error_message": instance.error_message,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/workflow-instances", methods=["GET"])
def get_all_workflow_instances():
    """获取所有工作流实例"""
    try:
        instances = workflow_manager.get_all_workflow_instances()
        instances_data = []

        for instance in instances:
            instances_data.append(
                {
                    "id": instance.id,
                    "workflow_template_id": instance.workflow_template_id,
                    "status": instance.status,
                    "created_at": instance.created_at.isoformat(),
                    "started_at": instance.started_at.isoformat() if instance.started_at else None,
                    "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
                    "error_message": instance.error_message,
                }
            )

        return jsonify({"success": True, "data": instances_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/workflows/import", methods=["POST"])
def import_workflow():
    """从JSON数据导入工作流"""
    try:
        data = request.json

        # 验证数据格式
        if not data.get("nodes") or not data.get("edges"):
            return jsonify({"success": False, "error": "无效的工作流数据格式，缺少nodes或edges"}), 400

        # 创建工作流
        workflow_data = workflow_manager.create_workflow(
            name=data.get("name", f"导入的工作流_{int(time.time())}"),
            description=data.get("description", "从JSON文件导入的工作流"),
        )

        # 更新节点和边数据
        workflow_manager.update_workflow(
            workflow_data["id"],
            name=workflow_data["name"],
            description=workflow_data["description"],
            nodes=data.get("nodes"),
            edges=data.get("edges"),
        )

        return jsonify({"success": True, "data": workflow_data})
    except Exception as e:
        import traceback

        print(f"Update workflow error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def parse_config_value(value):
    """解析配置值，提取默认值"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        # 解析 ${key:default} 格式
        inner = value[2:-1]  # 去掉 ${ 和 }
        if ":" in inner:
            key, default = inner.split(":", 1)
            return default if default != "-" else ""
        else:
            return ""
    return value


@app.route("/api/config", methods=["GET"])
def get_config():
    """获取当前配置"""
    try:
        config_file_path = os.path.join(config_path, "llm.yml")

        if not os.path.exists(config_file_path):
            return jsonify({"success": False, "error": "配置文件不存在"}), 404

        with open(config_file_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # 解析配置中的默认值
        def parse_config_section(section):
            if isinstance(section, dict):
                parsed = {}
                for key, value in section.items():
                    if isinstance(value, dict):
                        parsed[key] = parse_config_section(value)
                    else:
                        parsed[key] = parse_config_value(value)
                return parsed
            else:
                return parse_config_value(section)

        parsed_config = parse_config_section(config_data)

        return jsonify({"success": True, "data": parsed_config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/config", methods=["POST"])
def save_config():
    """保存配置"""
    try:
        data = request.json

        # 处理环境变量
        if "env" in data:
            env_vars = data["env"]
            for key, value in env_vars.items():
                if value:  # 只设置非空值
                    os.environ[key.upper()] = str(value)
                    print(f"设置环境变量: {key.upper()} = {value}")

        # 构建配置数据
        config_data = {
            "llm": {},
            "workflow": data.get(
                "workflow",
                {"dify": {"root-path": "config/", "instances": [{"name": "if_else_test", "path": "if-else-test.yml"}]}},
            ),
            "web": data.get("web", {"port": 8999, "host": "0.0.0.0", "workers": 8}),
            "vector": {},
            "embedding": {},
            "rerank": {},
        }

        # 处理LLM配置
        if "llm" in data:
            llm_config = data["llm"]

            # Moonshot配置
            if "moonshot" in llm_config:
                moonshot = llm_config["moonshot"]
                config_data["llm"]["moonshoot"] = {
                    "sk": f"${{llm.moonshoot.sk:{moonshot.get('sk', '-')}}}",
                    "enabled": moonshot.get("enabled", False),
                    "model-name": moonshot.get("model", "moonshot-v1-128k"),
                }
            else:
                # 保持原有的moonshot配置
                config_data["llm"]["moonshoot"] = {
                    "sk": "${llm.moonshoot.sk:-}",
                    "enabled": False,
                    "model-name": "moonshot-v1-128k",
                }

            # DeepSeek配置
            if "deepseek" in llm_config:
                deepseek = llm_config["deepseek"]
                config_data["llm"]["deepseek"] = {
                    "sk": f"${{llm.deepseek.sk:{deepseek.get('sk', '-')}}}",
                    "enabled": deepseek.get("enabled", True),
                    "model-name": deepseek.get("model", "deepseek-chat"),
                }

            # 通义千问配置
            if "tongyi" in llm_config:
                tongyi = llm_config["tongyi"]
                config_data["llm"]["tongyi"] = {
                    "sk": f"${{llm.tongyi.sk:{tongyi.get('sk', '-')}}}",
                    "enabled": tongyi.get("enabled", False),
                    "model-name": tongyi.get("model", "qwen-max"),
                }

            # OpenRouter配置
            if "openrouter" in llm_config:
                openrouter = llm_config["openrouter"]
                config_data["llm"]["openrouter"] = {
                    "sk": f"${{llm.openrouter.sk:{openrouter.get('sk', '-')}}}",
                    "enabled": openrouter.get("enabled", False),
                    "model-name": openrouter.get("model", "deepseek/deepseek-chat-v3-0324:free"),
                }

        # 处理向量数据库配置
        if "vector" in data:
            vector_config = data["vector"]
            if "dashvector" in vector_config:
                dashvector = vector_config["dashvector"]
                config_data["vector"]["dashvector"] = {
                    "api-key": f"${{vector.dashvector.api_key:{dashvector.get('api_key', 'sk-')}}}",
                    "endpoint": f"${{vector.dashvector.endpoint:{dashvector.get('endpoint', '-')}}}",
                    "cluster": f"${{vector.dashvector.cluster:{dashvector.get('cluster', 'vertex-vector')}}}",
                    "collection": f"${{vector.dashvector.collection:{dashvector.get('collection', '-')}}}",
                    "image-collection": f"${{vector.dashvector.image_collection:{dashvector.get('image_collection', '-')}}}",
                }

        # 处理嵌入模型配置
        if "embedding" in data:
            embedding_config = data["embedding"]

            if "dashscope" in embedding_config:
                dashscope = embedding_config["dashscope"]
                config_data["embedding"]["dashscope"] = {
                    "endpoint": f"${{embedding.dashscope.endpoint:{dashscope.get('endpoint', 'default')}}}",
                    "api-key": f"${{embedding.dashscope.api_key:{dashscope.get('api_key', '-')}}}",
                    "model-name": f"${{embedding.dashscope.model_name:{dashscope.get('model', 'text-embedding-v1')}}}",
                }

            if "bce" in embedding_config:
                bce = embedding_config["bce"]
                config_data["embedding"]["bce"] = {
                    "api-key": f"${{embedding.bce.api_key:{bce.get('api_key', '-')}}}",
                    "endpoint": f"${{embedding.bce.endpoint:{bce.get('endpoint', 'https://api.siliconflow.cn/v1/embeddings')}}}",
                    "model-name": f"${{embedding.bce.model_name:{bce.get('model', 'netease-youdao/bce-embedding-base_v1')}}}",
                }
            else:
                # 保持原有的bce配置
                config_data["embedding"]["bce"] = {
                    "api-key": "${embedding.bce.api_key:-}",
                    "endpoint": "${embedding.bce.endpoint:https://api.siliconflow.cn/v1/embeddings}",
                    "model-name": "${embedding.bce.model_name:netease-youdao/bce-embedding-base_v1}",
                }

        # 处理rerank配置
        if "rerank" in data:
            rerank_config = data["rerank"]

            if "bce" in rerank_config:
                bce = rerank_config["bce"]
                config_data["rerank"]["bce"] = {
                    "api-key": f"${{rerank.bce.api_key:{bce.get('api_key', '-')}}}",
                    "endpoint": f"${{rerank.bce.endpoint:{bce.get('endpoint', 'https://api.siliconflow.cn/v1/rerank')}}}",
                    "model-name": f"${{rerank.bce.model_name:{bce.get('model', 'netease-youdao/bce-reranker-base_v1')}}}",
                }
        else:
            # 保持原有的rerank配置
            config_data["rerank"]["bce"] = {
                "api-key": "${rerank.bce.api_key:-}",
                "endpoint": "${rerank.bce.endpoint:https://api.siliconflow.cn/v1/rerank}",
                "model-name": "${rerank.bce.model_name:netease-youdao/bce-reranker-base_v1}",
            }

        # 保存配置文件
        config_file_path = os.path.join(config_path, "llm.yml")

        # 备份原配置文件
        if os.path.exists(config_file_path):
            backup_path = config_file_path + f".backup.{int(time.time())}"
            os.rename(config_file_path, backup_path)
            print(f"原配置文件已备份到: {backup_path}")

        # 写入新配置
        with open(config_file_path, "w", encoding="utf-8") as f:
            # 添加配置文件头部注释
            f.write("# VertexFlow Configuration File\n")
            f.write("# 通过docker env可以注入相关的配置，作为修改值\n")
            f.write("# 例如ll.deepseek.sk，则通过llm_deepseek_sk环境变量\n")
            f.write("# 在docker启动时设置-e llm_deepseek_sk=?\n")
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"配置已保存到: {config_file_path}")

        return jsonify({"success": True, "message": "配置保存成功"})

    except Exception as e:
        import traceback

        print(f"保存配置错误: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8500)
