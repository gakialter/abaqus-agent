# 学生 3 分钟上手（abaqus-agent）

不会命令行也能用。记住下面两张流程图即可。

## 第一次（只做一次）

```
下载 ZIP  →  解压  →  双击 install.bat  →  双击 doctor.bat  →  双击 start_abaqus_agent.bat
```

1. 从 GitHub **Code → Download ZIP** 下载并解压（不需要 Git）。
2. 双击 `install.bat`。没找到 Abaqus 就按提示输入 `abaqus.bat` 路径。
3. 双击 `doctor.bat`，看到 **Overall: READY** 就 OK。
4. 双击 `start_abaqus_agent.bat`，等它显示 “Abaqus Agent is started”（Abaqus 窗口别关）。

## 以后每天

```
双击 start_abaqus_agent.bat  →  打开豆包 Work  →  上传题目  →  发提示词
```

推荐提示词：

> 使用 abaqus-agent Skill 完成这道 Abaqus 任务。严格以我提供的题目为唯一事实源，不得自行补参数；先过 Problem Fidelity Gate，再真实控制 Abaqus 完成建模、求解、ODB 后处理和物理验证，全部 Gate 通过后才算完成。

## 出问题了

双击 `doctor.bat`，把输出发给豆包 Work。

详细说明见 [bootstrap_for_doubao_work.md](bootstrap_for_doubao_work.md)。
