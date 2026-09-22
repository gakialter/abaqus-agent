# Abaqus Agent × 豆包 Work（零基础一键部署）

这份文档给**第一次使用**的同学。你不需要懂 MCP、FastMCP、文件 IPC、Abaqus kernel、Python 虚拟环境或环境变量。照着做即可。

---

## 你需要什么

- Windows 电脑
- 已经安装好并能正常打开的 **Abaqus/CAE**（本仓库在 2026 版上验证过）
- 已安装官方桌面版 **豆包 Work**（支持“工作任务 / 本地电脑 / 操作电脑”的版本）
- 本仓库（已下载并解压到本地）

> 本安装**不会**修改 Abaqus 安装目录、**不会**改 License、**不会**往 Abaqus 自带 Python 里装东西。

---

## 第一次安装（约 5 分钟）

1. **下载仓库**
   - 打开 <https://github.com/gakialter/abaqus-agent>
   - 点 **Code → Download ZIP**，然后解压到一个**纯英文、没有奇怪权限**的目录，例如：
     - `C:\Users\你的名字\Desktop\abaqus-agent`
     - 或 `D:\Tools\abaqus-agent`
   - 不需要 `git clone`，不需要懂 Git。

2. **双击 `install.bat`**
   - 它会自动找 Python、找 Abaqus、建一个独立的 `.venv`、写好配置。
   - 如果它**没自动找到 Abaqus**，会停下来让你输入 `abaqus` 命令或 `abaqus.bat` 的完整路径，按提示输入即可。
   - 看到结尾类似：
     ```
     [OK] Python ...
     [OK] Abaqus ...
     [OK] Environment ...
     [OK] Skill ...
     [OK] abaqus-agent installed
     Next: double-click start_abaqus_agent.bat
     ```

3. **同步 Skill（第一次或升级后做一次）**
   - 如果 `install.bat` 自动检测到了豆包 Work 的 Skill 目录，它会把 `SKILL.md` 和 `references/` 同步过去，无需你操作。
   - 如果没有检测到，仓库里会生成一个 `doubao_skill_install.txt`。这时在豆包 Work 里粘贴本文档最后一节“给豆包 Work 的自安装提示词”即可。

4. **双击 `start_abaqus_agent.bat`**
   - 它会打开 Abaqus/CAE 并自动加载桥接。
   - 等到黑窗口显示：
     ```
     ================================================
     Abaqus Agent is started.
     Now open Doubao Work and upload your task.
     ================================================
     ```
   - **Abaqus 窗口请保持打开**，工作期间不要关。

5. **打开豆包 Work**，开始用。

---

## 第一次验证（强烈建议做一次）

双击 `doctor.bat`。看到下面这样就说明一切正常：

```
Environment
-----------
Python       PASS
Abaqus       PASS
...
Skill        PASS
Bridge       PASS
Ping         PASS
Kernel       PASS
Overall: READY
```

如果是 `Overall: NOT READY`，它会给出具体修复提示。把 `doctor.bat` 的完整输出截图发给豆包 Work，让它帮你看。

---

## 以后每天怎么用（3 步）

1. 双击 `start_abaqus_agent.bat`，等 Abaqus 启动并显示 “Abaqus Agent is started”。
2. 打开豆包 Work。
3. 上传你的题目（PDF / DOCX / 图片 / 文字），用下面这段提示词发起任务。

> 以后**不需要**再运行 `install.bat`，除非你换了机器或重装了 Abaqus。

---

## 在豆包 Work 里怎么说（推荐默认提示词）

把下面这段连同你的题目一起发给豆包 Work：

```
使用 abaqus-agent Skill 完成这道 Abaqus 任务。
严格以我提供的题目/PDF/DOCX/图片为唯一事实源。
不得自行补参数。
先通过 Problem Fidelity Gate，
然后真实控制 Abaqus 完成建模、求解、ODB 后处理和物理验证。
只有全部 Gate 通过后才能宣布完成。
```

---

## 如果打不开 / 不正常

- 双击 `doctor.bat`。
- 把它输出的全部文字复制/截图发给豆包 Work，说“帮我诊断 abaqus-agent 状态”。
- 常见情况：
  - Abaqus 还在启动 → 等 30 秒再跑一次 `doctor.bat`。
  - 提示找不到 Abaqus → 重新双击 `install.bat`，在提示时输入正确的 `abaqus.bat` 路径。
  - 提示 `.venv` 不存在 → 重新双击 `install.bat`。

---

## 目录里这些文件是干嘛的

| 文件 | 作用 |
|------|------|
| `install.bat` | 第一次安装 / 修复（双击） |
| `start_abaqus_agent.bat` | 每天启动 Abaqus + 桥接（双击） |
| `doctor.bat` | 一键体检（双击） |
| `SKILL.md` | 给 AI 的使用说明（不要手改） |
| `references/` | 建模/求解/后处理知识（不要手改） |

---

## 给豆包 Work 的自安装提示词

仅当 `install.bat` 没能自动检测到 Skill 目录时才需要。在豆包 Work 里新建对话，粘贴下面这段：

```
读取本地 abaqus-agent 仓库。
请把仓库中的：
SKILL.md
references/
安装/同步到当前豆包 Work 实际使用的 abaqus-agent Skill runtime。
要求：
- 先检测当前版本真实 runtime，不猜路径
- 如果已有旧版本，先备份
- 仓库为唯一真源
- 只同步 SKILL.md + references/
- 不复制 scripts/MCP/ODB/validation
- 同步后检查所有 reference 链接
- 运行 regression-checklist.md 的静态 A–J smoke test
- 完成后报告 runtime 路径和测试结果
```

仓库根目录通常是 `C:\Users\你的用户名\Desktop\abaqus-agent`（或你解压的位置）。
