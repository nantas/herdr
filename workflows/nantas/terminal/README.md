# Windows 终端配置

这里保存个人工作流的可复用配置片段，不包含完整用户配置、连接信息或备份，不修改 Herdr 内置或远程发布的检测规则。

## WezTerm 右键

将 [wezterm-mouse.lua](wezterm-mouse.lua) 返回的条目合并到 `%USERPROFILE%\.wezterm.lua` 的 `config.mouse_bindings` 中。已有配置不要整体替换；删除同一右键事件中设置了 `mouse_reporting = true` 且执行 `PasteFrom` 的条目。

普通命令行保留右键粘贴；Herdr 启用鼠标报告时，右键交给 Herdr，工作区菜单可以打开。保存后 WezTerm 默认自动重载；禁用了自动重载时使用 Reload Configuration 动作。需要快捷键粘贴时可在已有 `config.keys` 中保留 `Alt+V` 或 `Shift+Insert` 的 `PasteFrom 'Clipboard'` 绑定。

用 `wezterm show-keys` 检查配置能否加载，再实际右键点击 Herdr 工作区。回退时恢复修改前的鼠标绑定；备份只留在本机。

## pi 工作状态

[pi.toml](pi.toml) 基于远程检测规则 `2026.10.01.1`，仅放宽工作提示前后的空白。pi 1.4.0 实际显示的 ` ⠴ Working` 带行首空格，原规则不匹配，于是 Herdr 回退为 `idle`（绿色空心圈）。此覆盖不添加阻塞检测；权限确认等状态需要真实界面证据后再补充。

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

本地覆盖优先于远程更新。官方规则修复后，先比较新规则，移除这份覆盖，再执行相同的 reload 命令恢复远程规则；若安装前有自定义覆盖，应恢复原文件。无需重启服务器或 pi。

## 2026-10-24 验证记录

- Windows、Herdr 0.9.5、pi 1.4.0。
- WezTerm 配置加载成功，用户确认工作区右键菜单恢复。
- pi 的进程识别正常；实时检测缓冲区出现带一个行首空格的 `⠴ Working`，原规则未命中，回退为 `idle`。
- 用 `herdr agent explain --file ... --agent pi --json` 重放该工作提示：修复前带空格为 `idle`、去掉空格为 `working`；加载覆盖后带空格为 `working`，空内容为 `idle`。
- 运行中的 `work` 服务器热重载成功，检测来源确认是本地覆盖。未启动付费模型任务；尚未验证修复后的完整实时工作到闲置转换或阻塞状态。
