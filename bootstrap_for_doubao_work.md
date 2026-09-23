# Abaqus Agent 与豆包 Work：待验证的集成说明

本仓库不自动写入豆包 Work 的隐藏目录，也尚未验证当前豆包 Work UI 的 Skill 包格式。

1. 下载 ZIP，解压到可写目录。
2. 运行 `install.bat`，按提示提供 Abaqus 启动命令。运行 `doctor.bat` 检查 `INSTALLED`。
3. 运行 `start_abaqus_agent.bat`，等待 `BRIDGE_READY`。已有 owner 但不响应时启动器报告 BUSY/UNRESPONSIVE，不会再开第二会话。
4. 在产品支持的 UI 导入 `SKILL.md` 及 `references/`，确认引用可以解析。
5. 如产品支持自定义 STDIO MCP 连接，设置 command 为 `<repo>\.venv\Scripts\python.exe`，argument 为 `<repo>\mcp_server.py`，environment 为 `ABAQUS_MCP_HOME=<repo>\mcp_home`。
6. 在产品内检查工具发现、ping，以及 Abaqus 重启后的重连。未完成这些真实 UI 检查时 `INTEGRATION_READY=EXTERNAL/UNVERIFIED`。

路径可以包含空格或中文。不要复制到第二工作区，也不要运行旧 BAT 配置文件。
