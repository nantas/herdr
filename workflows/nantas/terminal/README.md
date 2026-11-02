# Windows 终端配置

这里保存个人工作流的可复用配置片段，不包含完整用户配置、连接信息或备份，不修改 Herdr 内置或远程发布的检测规则。

## WezTerm 右键

将 [wezterm-mouse.lua](wezterm-mouse.lua) 返回的条目合并到 `%USERPROFILE%\.wezterm.lua` 的 `config.mouse_bindings` 中。已有配置不要整体替换；删除同一右键事件中设置了 `mouse_reporting = true` 且执行 `PasteFrom` 的条目。

普通命令行保留右键粘贴；Herdr 启用鼠标报告时，右键交给 Herdr，工作区菜单可以打开。保存后 WezTerm 默认自动重载；禁用了自动重载时使用 Reload Configuration 动作。需要快捷键粘贴时可在已有 `config.keys` 中保留 `Alt+V` 或 `Shift+Insert` 的 `PasteFrom 'Clipboard'` 绑定。

用 `wezterm show-keys` 检查配置能否加载，再实际右键点击 Herdr 工作区。回退时恢复修改前的鼠标绑定；备份只留在本机。

## Herdr UI

以下基于 2026-10-24 的 Windows 实测：Herdr UI 20261020.1、Herdr 0.9.5、Windows PowerShell 5.1。Herdr UI 是独立客户端；本次安装没有升级或重启 Herdr daemon。

### 安装与排查

官网入口为 `https://herdrui.dev/#install`，PowerShell 安装命令为：

```powershell
irm https://herdrui.dev/install.ps1 | iex
```

脚本安装到 `%LOCALAPPDATA%\Programs\Herdr UI`，添加用户 PATH 和开始菜单快捷方式。此次安装的 ZIP 通过脚本 SHA-256 校验，主程序、launcher、快捷方式目标及 PATH 均已核对。已有终端可能需要重开才能使用新增 PATH；也可直接使用下面示例中的绝对路径。

- 若报 `Herdr UI has no Windows build for `，且末尾架构为空，检查 `[Runtime.InteropServices.RuntimeInformation]::OSArchitecture`。此次原报错未复现：新开的 32 位及 64 位 PowerShell 均返回 `X64`，正常加载 profile 和 `-NoProfile` 均通过检测。不能据此认定没有 Windows 构建，或将原因归结为 PowerShell 5.1；原会话的空值原因尚未查明。
- 若版本查询报 GitHub API rate limit，属于独立的网络/API 问题。此次用已认证的 `gh api repos/penso/herdr-gpui/releases/latest --jq .tag_name` 确认版本，仅在内存中替换官网脚本的版本查询语句，保留其下载、校验和安装流程后成功。将来须重新查询版本并检查脚本，不应永久固定此次版本或跳过校验，也不把认证 token 写入脚本或日志。

### 本机会话与远端连接

一个 UI 窗口可以同时连接 Local 和已保存的 SSH 主机。Local 使用的会话与远端连接的会话独立；连接本机 `default` 时仍可看到远端工作区，但不会因此看到本机 `work` 的工作区。

先查询实际会话和工作区，再为运行中的 UI 打开本机 `work` 窗口：

```powershell
$ui = "$env:LOCALAPPDATA\Programs\Herdr UI\herdr-gpui.exe"
herdr session list
herdr --session default workspace list
herdr --session work workspace list
& $ui status
& $ui window list
& $ui window new --session work
```

此次新窗口已确认 Local 在线并显示 `work` 的活动工作区；原窗口保留，原有 Agent 未重启。不要通过重建工作区或停止服务器解决客户端连错会话。窗口 ID、工作区 ID 应实时查询，不保存历史值。CLI 默认按调用者工作区选择窗口；提示找不到对应窗口时，用 `window list` 返回的 ID 通过 `--window ID` 明确指定目标。

### 字体与默认字号

`Ctrl+Shift+,` 打开 UI 设置。以下是可选设置示例，不是本次已执行的配置变更；先用 `font list` 确认字体已安装：

```powershell
$ui = "$env:LOCALAPPDATA\Programs\Herdr UI\herdr-gpui.exe"
& $ui font list
& $ui font set "JetBrainsMono Nerd Font Mono"
& $ui config set terminal.size 16
& $ui config check
```

该版本 `font set` 修改所有字体 face；不要把它当成仅修改终端字体的命令。`config set` 的修改保存到用户覆盖文件并由运行中的 UI 即时应用。`font reset` 恢复默认字体，`config unset terminal.size` 移除自定义默认字号。

临时调整当前窗口字号用 `Ctrl+Shift+=`、`Ctrl+Shift+-`，`Ctrl+0` 恢复默认字号；CLI 对应 `ui font-size`，它与持久化的 `config set terminal.size` 不同。

用 `config path` 查询实际配置路径。在本次 Windows 环境中，用户覆盖文件为 `%APPDATA%\herdr\config-gpui.local.toml`；`config-gpui.toml` 是每个版本会重写的默认值文件，不应作为用户配置维护。Herdr daemon 的 `config.toml` 是另一个配置文件。仅记录可复用命令，不将完整个人配置或备份复制进仓库。本次只检查了字体列表、快捷键和配置命令，未修改字体，也未进行重启后的字体持久化验收。

## pi 工作状态

[pi.toml](pi.toml) 与本仓库 `src/detect/manifests/pi.toml`（`2026.11.02.1`）保持一致：独立工作状态行容忍行首缩进与尾缀，新增 `osc_title` 中的 `:running...` 命中，边框嵌入形态不变。pi 1.4.0 实际显示的 ` ⠴ Working` 带行首空格，旧规则 `2026.10.01.1` 不匹配，于是 Herdr 回退为 `idle`（绿色空心圈）。此覆盖不添加阻塞检测；使用 pi-ask 等待回答时的阻塞状态通过下文的 Herdr Pi 集成上报，其他权限确认界面需单独验证。

在运行 pi 的 Herdr 服务器所在节点安装，而不是仅在远程控制端安装。Windows 默认目标为 `%APPDATA%\herdr\agent-detection\pi.toml`；若设置 `XDG_CONFIG_HOME`，改用其下的 `herdr\agent-detection\pi.toml`。以下在仓库根目录运行，已有覆盖时停止，先比较并合并，不直接覆盖：

```powershell
$configRoot = if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } else { $env:APPDATA }
$destination = Join-Path $configRoot 'herdr/agent-detection/pi.toml'
if (Test-Path -LiteralPath $destination) { throw '已有本地覆盖，请先比较并合并' }
New-Item -ItemType Directory -Force -Path (Split-Path $destination) | Out-Null
Copy-Item -LiteralPath workflows/nantas/terminal/pi.toml -Destination $destination
herdr --session work server reload-agent-manifests
herdr --session work agent list
```

对列表返回的实际 pane ID 执行 `herdr --session work agent explain <pane-id> --json`，确认 `manifest_source` 指向本地覆盖。会话名按实际环境调整；若环境设置了 Herdr socket overrides，应先确认其指向目标服务器。

本地覆盖优先于远程更新。安装的 Herdr 发布版携带 ≥ `2026.11.02.1` 的内置或远程 pi 规则后，先比较新规则，移除这份覆盖，再执行相同的 reload 命令恢复；若安装前有自定义覆盖，应恢复原文件。无需重启服务器或 pi。

### pi-ask 等待回答显示为空闲

2026-11-01 排查 Windows Local / `work` 会话时，pi 正常执行任务能被检测为 `working`，但打开 pi-ask 问答后变为绿色空心圈。`agent explain` 显示没有命中屏幕规则，回退原因是 `default_known_agent_idle_fallback`；这是服务器状态判断，Herdr UI 显示的是服务器返回的状态。

本机使用 pi-config 声明的 `git:github.com/jwu/pi-ask`，磁盘版本为 0.3.0。该版本已通过共享事件总线发送 `herdr:blocked`：问答打开时发送 `{ active: true, label: "等待回答" }`，结束时发送 `{ active: false }`。Herdr Pi 集成负责接收事件并上报状态。此次 Windows 缺少该集成，`herdr integration status` 显示 `pi: not installed`。

在**运行 pi 的节点**执行以下命令；控制端连接远程节点时，应在远程节点安装，而不是仅在 Windows 控制端安装：

```powershell
herdr integration install pi
herdr integration status
```

此次 Herdr 0.9.5 安装后显示 `pi: current (v9)`，默认文件为 `%USERPROFILE%\.pi\agent\extensions\herdr-agent-state.ts`。设置了 `PI_CODING_AGENT_DIR` 时，以安装命令输出的实际路径为准。该文件由 Herdr 管理，不手工修改；此次没有修改 pi-config 或运行全量配置同步。

安装文件后，已有 pi 进程还需加载扩展。等当前任务结束，在 pi 输入框执行 `/reload`；也可以退出并恢复原 Pi 会话。无需重启 Herdr 服务器或 Herdr UI。问答等待状态由事件上报，保留现有 `pi.toml` 即可，无需为此新增屏幕规则。

pi-ask 的事件覆盖整段问答生命周期：隐藏问答仅折叠界面，仍应保持阻塞；提交、取消或异常退出通过 `finally` 清除等待状态。相关实现入口：

- pi-ask 包内 `src/herdr-state.ts` 和 `src/ui/controller.ts`：发送等待事件及清理。
- [Herdr Pi 集成](../../../src/integration/assets/pi/herdr-agent-state.ts)：监听事件，并根据问答及 Agent 活动状态上报 `blocked`、`working` 或 `idle`。

验证时先用 `herdr --session work agent list` 查询实际 pane ID，再结合 UI 检查“执行任务 → 打开问答 → 隐藏/展开 → 提交或取消 → 继续工作 → 完成”。不要把整个问答底部快捷键提示当成主要检测信号：提示可隐藏，快捷键可重绑定，折叠后界面也不同。

### 2026-11-01 验证结果

- Windows、Herdr 0.9.5、pi 1.4.0；安装前实时采集到 ` ⠴ Working`，两条工作规则均命中，服务器返回 `working`。
- 本机 Herdr Pi 集成从未安装变为 `current (v9)`；服务器、UI 和现有检测覆盖未改动。
- 安装后用户确认：问答等待时已正确显示红圈（阻塞）。
- 隐藏/展开、取消、异常退出及结束后的完整转换尚未逐项实测；上述生命周期说明来自源码，不能视为这些场景均已验收。

## 2026-10-24 验证记录

- Windows、Herdr 0.9.5、pi 1.4.0。
- WezTerm 配置加载成功，用户确认工作区右键菜单恢复。
- pi 的进程识别正常；实时检测缓冲区出现带一个行首空格的 `⠴ Working`，原规则未命中，回退为 `idle`。
- 用 `herdr agent explain --file ... --agent pi --json` 重放该工作提示：修复前带空格为 `idle`、去掉空格为 `working`；加载覆盖后带空格为 `working`，空内容为 `idle`。
- 运行中的 `work` 服务器热重载成功，检测来源确认是本地覆盖。未启动付费模型任务；尚未验证修复后的完整实时工作到闲置转换或阻塞状态。
