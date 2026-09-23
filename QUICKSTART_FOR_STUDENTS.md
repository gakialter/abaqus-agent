# 学生上手

下载 ZIP → 解压到可写目录 → `install.bat` → `doctor.bat` → `start_abaqus_agent.bat`。

首次安装使用外部 Python 3.11。doctor 分别显示 `INSTALLED`、`BRIDGE_READY` 和 `INTEGRATION_READY`；启动前 bridge 未运行是正常状态。启动后必须见到真实 IPC ping 验证的 `BRIDGE_READY`。

接着在所用产品的正式 UI 中导入 `SKILL.md` 和 `references/`，创建本地 STDIO MCP 连接：

- command: `<repo>\.venv\Scripts\python.exe`
- argument: `<repo>\mcp_server.py`
- environment: `ABAQUS_MCP_HOME=<repo>\mcp_home`

最后在该产品内验证工具发现与 ping。豆包 Work 的导入格式和连接步骤尚待真实 UI 验证；不要把安装成功视为集成成功。详细说明见 [部署说明](bootstrap_for_doubao_work.md)。
