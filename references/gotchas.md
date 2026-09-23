# Abaqus 2026 / Windows 实操坑位（实测）

按这里避坑，别在 README 上栽。

## 启动与进程
- Abaqus 命令通常是 `abaqus`（实为某个 `.bat` → `SMALauncher.exe`）。不在 PATH 时常见于
  `C:\Program Files\SIMULIA\EstProducts\<ver>\win_b64\code\bin\abq<ver>.bat` 或自定义目录。
- 用 `abaqus cae script="<abs path>"` 启动 GUI 并在启动时跑内核脚本；脚本里 `mcp_loop()`
  是阻塞的，**这正是要的**：主内核线程持续轮询命令文件，GUI 窗口照常可用、可截图。
- 后台线程模式 `mcp_start()` 官方标 experimental；Abaqus API 从非主线程调用有风险，**用 blocking**。

## API 差异（2026 实测）
- `region.getByBoundingBox(...)` 要 **6 个独立 float 参数** `(xmin,ymin,zmin,xmax,ymax,zmax)`，
  传一个 tuple 会报 `arg1; found tuple, expecting float`。
- `session.printToFile(format=...)` 必须用 `from abaqusConstants import PNG,SVG,TIFF` 的常量。
  不要 `getattr(session,'PNG',session.PNG)`——Abaqus 2026 的 Session 对象没有 `.PNG` 属性，
  且 getattr 默认值会被提前求值直接抛 `AttributeError`。
- 模型重名会报错。每次建模型前先 `del mdb.models['X']`（job 同理）。
- `execute_script` 在插件里把 `print` 重定向成列表回传，脚本里用 `print(json.dumps(...))`
  把结果带回来；`mdb`/`session` 已自动注入。

## 外部 Python 隔离
- Abaqus 自带 Python 是 3.10（`win_b64\tools\SMApy\python3.10\`）。**不要**往它里面 pip install。
- 外部 MCP server 使用独立 Python 3.11 venv；当前发布基线是 `mcp==1.30.0`，并核对 `FastMCP` 可导入。其他 Python 版本不在本次发布支持范围。

## 安全边界
- `execute_script` 在 Abaqus 内核里跑任意 Python——只接可信客户端/可信脚本，别公网暴露。
- 不改 `C:\Program Files\SIMULIA`、不动 License、不改全局 `abaqus_v6.env`。
  一切装在用户工作目录；用 `ABAQUS_MCP_HOME` 环境变量把 IPC 目录指到隔离工作区。

## 停掉
- 运行仓库根目录的 `stop_mcp.py`；停止请求绑定当前 owner session。旧会话的 `stop.flag` 不会停止新会话。
