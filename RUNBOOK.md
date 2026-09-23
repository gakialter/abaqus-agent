> Historical/local reproduction, non-portable paths and observations. Use README.md for current installation.

# Abaqus 2026 × AI Agent 集成运行手册

最终方案：**Cai-aa/abaqus-mcp v4.0（文件 IPC）+ 独立 venv**，已在 Abaqus/CAE 2026 (Python 3.10) 上端到端跑通。

## 1. 最终架构

```
AI Agent (Doubao / Cursor / Claude / 自写 client.py)
        │  文件 IPC：写 commands/cmd_*.json，轮询 results/*.json
        ▼
  mcp_server.py  (独立 venv, mcp 1.30)   ← 仅给标准 MCP 客户端用
        │
        ▼  同一套文件协议
  abaqus_mcp_plugin.py  (在 Abaqus/CAE 内核里运行, blocking 轮询)
        │
        ▼
  Abaqus/CAE 2026  →  Job(CantileverJob)  →  .odb  →  printToFile 截图
```

- Abaqus 端插件**只用标准库**，没有往 Abaqus 自带 Python 装任何 pip 包。
- 外部 MCP server 跑在独立 venv（系统 Python 3.11），与 Abaqus Python 完全隔离。
- **没有改动** `C:\Program Files\SIMULIA` 下任何文件，**没有动 License**，**没有**改 `abaqus_v6.env`，**没有**往 `~/abaqus_plugins` 装菜单。

## 2. 安装位置（全部在隔离目录）

根目录：`C:\Users\27296\Desktop\abaqus-agent`

| 路径 | 作用 |
| --- | --- |
| `abaqus_start_mcp.py` | Abaqus 端启动脚本（被 `abaqus cae script=` 调用） |
| `abaqus_mcp_plugin.py` | Abaqus 内核插件（已打截图 bug 补丁） |
| `mcp_server.py` | 标准 MCP server（FastMCP），给 MCP 客户端 |
| `client.py` | 直连驱动器（和 mcp_server 同一协议，Agent 自测用） |
| `validate.py` | 端到端验证（建梁→提交→读 ODB） |
| `shot.py` | 视口/云图截图 |
| `.venv\` | 独立 Python 3.11 环境，已装 `mcp==1.30.0` |
| `mcp_home\` | 全部 IPC 文件（commands/results/status/log） |
| `work\` | Job 工作目录，`.odb/.inp/.dat` 等都在这里 |

## 3. 改动过的文件（最小集）

1. `abaqus_mcp_plugin.py` — 修了 `get_viewport_image` 里 `getattr(session, fmt, session.PNG)` 在 Abaqus 2026 上抛 `'Session' object has no attribute 'PNG'` 的 bug，改为从 `abaqusConstants` 取 `PNG/SVG/TIFF`。
2. 外部 venv 固定 `mcp<2`（装到 1.30.0）。仓库代码用的是 FastMCP v1 API；mcp 2.x 已把 FastMCP 改名 MCPServer，不做迁移就直接钉版本。
3. 其余都是**新建**文件，未覆盖任何 Abaqus 原文件。

## 4. 最短启动流程（以后照这个来）

```powershell
# (1) 启动 Abaqus/CAE 2026，自动加载插件并进入轮询
set ABAQUS_MCP_HOME=C:\Users\27296\Desktop\abaqus-agent\mcp_home
abaqus cae script="C:\Users\27296\Desktop\abaqus-agent\abaqus_start_mcp.py"
# 等 ~20-40 秒，看到 mcp_home\status.json 里 status="running"

# (2) [可选] 启动标准 MCP server（给 Cursor/Claude Desktop 等 MCP 客户端）
C:\Users\27296\Desktop\abaqus-agent\.venv\Scripts\python.exe `
  C:\Users\27296\Desktop\abaqus-agent\mcp_server.py

# (3) Agent 即可操作。直接自测：
C:\Users\27296\Desktop\abaqus-agent\.venv\Scripts\python.exe `
  C:\Users\27296\Desktop\abaqus-agent\client.py
```

MCP 客户端配置（Cursor / Claude Desktop `.mcp.json`）：
```json
{
  "mcpServers": {
    "abaqus": {
      "command": "C:/Users/27296/Desktop/abaqus-agent/.venv/Scripts/python.exe",
      "args": ["C:/Users/27296/Desktop/abaqus-agent/mcp_server.py"],
      "env": { "ABAQUS_MCP_HOME": "C:/Users/27296/Desktop/abaqus-agent/mcp_home" }
    }
  }
}
```

停止：在 Abaqus 命令行跑 `mcp_stop()`，或 `echo $null > mcp_home\stop.flag`。

## 5. Agent 能调用的能力（MCP tools）

- `check_abaqus_connection` / `ping` — 连通性
- `execute_script(script)` — 在 Abaqus 内核里跑任意 Python（`mdb`/`session` 已注入，`print` 输出回传）
- `get_model_info` — 零件/材料/分析步/载荷/边界条件/装配实例
- `list_jobs` / `submit_job(name)` — 列作业、提交并等待完成
- `get_odb_info(path)` — 只读打开 ODB，返回分析步/帧/实例元数据
- `get_viewport_image` — 视口 PNG/SVG/TIFF 截图（base64）

## 6. 测试模型（最小验证）

3D 悬臂梁：100×10×10 mm，Steel（E=210000 MPa, ν=0.3），x=0 端 Encastre，自由端 4 个角节点各 -50 N (Z)，Static General。

| 指标 | 实测 | 梁理论手算 |
| --- | --- | --- |
| Job 状态 | **COMPLETED** | — |
| 最大位移 | **0.403 mm** | ≈0.38 mm |
| 最大 von Mises | **100.2 MPa**（云图固定端峰值 ≈109 MPa） | ≈120 MPa |

截图：`work\viewport_cantilever.png`（Abaqus/Standard 2026 实渲染，S,Mises 云图，固定端红、自由端蓝）。

## 7. 已知限制

- Abaqus 内核轮询用 **blocking 模式**（最稳）；此期间 Abaqus/CAE 的命令行不能再手敲，但 GUI 窗口正常、截图正常。
- 后台线程模式（`mcp_start`）仓库自己标了 experimental，未使用。
- `execute_script` 在 Abaqus 内核里跑任意代码——只接可信客户端/可信脚本，不要暴露到公网。
- `get_viewport_image` 在当前运行会话里仍是旧代码；下次重启 Abaqus 后补丁生效。本次截图是走 `execute_script` + 正确 API 出的。
- ODB 数值提取是自写脚本（插件自带的 `get_odb_info` 只返回元数据），已在 `validate.py` 里示范。

## 8. 是否建议长期用

**建议**。理由：Abaqus 端零依赖、跨版本（v2026 验证通过）、纯文件 IPC 在 Windows 上没有 socket/端口坑、不碰安装目录与 License。建议把 `abaqus_skills`（jasonanewcoder 那个仓库）作为 Agent 的"建模/网格/作业知识"参考一起喂给模型，本仓库提供"真正能控制 Abaqus 的手"。
