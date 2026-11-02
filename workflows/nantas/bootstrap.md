# 新机器初始化与本机配置同步

本页是 agent 在新机器（或需要重新同步的机器）上部署本 fork 个人工作流的唯一入口。逐节执行到"完成判据"即停；按机器矩阵跳过不适用的步骤。细节回到对应功能文档，本页不重复其内容，只维护顺序、来源与判据。

重新同步不以当前机器完成为结束。先按[同步目标](#同步目标)列出当前可达的局域网设备，再把本次同步中必须落在执行节点上的步骤逐台核对。只改控制端时，远端 pane 仍按远端服务器的旧规则显示空心圈。

机器特定数据（SSH 目标、局域网地址、外置盘路径）不随本页复制，按 README 的[节点与会话](README.md#节点与会话)在新机器上现查现填。已保存机器的地址以 `herdr machine list --json` 当次返回的 `target` 为准，不把 README 里的旧地址写进命令。

## 机器矩阵

| 步骤 | 服务器节点（跑 pi 的 Mac/Linux） | Windows 控制端 |
|------|------|------|
| 通用前置 | ✅ | ✅ |
| work 会话自启动 | ✅ | 见 [terminal/README.md](terminal/README.md)（任务计划） |
| 交互颜色 / 启动器 / Git 弹窗 | ✅ | Windows 变体见 terminal/README.md |
| pi 工作状态检测覆盖 | ✅ | ✅（部署副本 `terminal/pi.toml`） |
| Herdr Pi 集成 | ✅（在跑 pi 的节点装） | ✅ |
| Herdr UI（图形端） | ✅ 可选 | 见 terminal/README.md 的 Herdr UI 节 |
| 机器互连 | ✅ | ✅ |
| neonspark 私有配置 | 见 [README 对应节](README.md#neonspark-私有配置同步) | 同左 |

## 同步目标

每次按本页同步或核对配置时，先建目标集合，再执行后面的服务器节点步骤。

```bash
herdr machine list --json
herdr machine status <label>
```

- 当前机器始终在目标集合内。
- `enabled: false` 的已保存机器跳过，在结果里写明 label。
- `herdr machine status <label>` 为 reachable 的机器加入目标集合。SSH 目标用该条的 `target`，会话名用该条的 `session`。
- 非 reachable：不在该节点写文件，结果里写明 label 与 status 原因。

文件复制和 `herdr integration install` 不会经 `herdr --machine` 转发。对远端用 `ssh -o BatchMode=yes -o ConnectTimeout=8 "$target"`，不要交互式认证。`herdr --machine <label> server agent-manifests` 和 `reload-agent-manifests` 可以在控制端转发，用来核对和重载，不能替代在节点上写文件。

本次同步涉及的服务器节点步骤，凡完成判据依赖跑 pi 或 Herdr 服务器的那台机器，就对目标集合逐台检查；未达到判据就在该节点执行同一步。当前必须这样执行的是下文 2.3 与 2.4。自启动、键位与本机路径、Herdr UI、机器互连、neonspark 私有配置不自动扇出；用户点名要同步那些项时，再按对应小节在目标节点执行。

完成判据：结果逐台写明已启用机器是 reachable 还是不可达；每台 reachable 机器都有 2.3 与 2.4 的完成判据，而不只是当前机器。

## 1. 通用前置

- Herdr stable（服务器节点 0.9.5+，`~/.local/bin/herdr`）、Python 3、SSH，`herdr` 在 PATH。
- 完成判据：`herdr status` 报告 server running；`python3 --version` ≥ 3.10。

## 2. 服务器节点

### 2.1 work 会话自启动

按 README 自启动小节部署：macOS 用 `presets/session-server.py` 包装脚本 + `~/Library/LaunchAgents/local.herdr.work.plist`（RunAtLoad），Windows 用任务计划。外置盘路径在 launchd 首次启动会触发 TCC 授权，需用户在桌面确认。

完成判据：`herdr --session work status` 返回 `detached_server_daemon: true`，且直接 SSH attach 不再提示重启服务器。

### 2.2 交互颜色 / 启动器与预设 / Git 弹窗 / config.toml 键位

按 README 各节安装：`shell/interactive-colors.sh`（zsh）或 PowerShell profile 版本、`presets/herdr-project.py` + `presets.json`（本机路径现查现填）、`git/herdr-git-status.py`。将 `presets/picker.toml`（项目选择弹窗）与 `git/popup.toml`（Git 文件弹窗）合并进 `~/.config/herdr/config.toml`，并按习惯加上 `onboarding = false` 与主题 `one-dark`（`auto_switch = false`）。

完成判据（仓库根目录）：

```bash
just nantas-presets-test && just nantas-git-test
python3 workflows/nantas/shell/test_colors.py
herdr config check && herdr server reload-config
```

Windows 变体（`windows-curses`、`.cmd` 包装、GBK 解码注意事项）以 terminal/README.md 为准。

### 2.3 pi 工作状态检测覆盖

对[同步目标](#同步目标)中每台跑 pi 的 Unix 服务器节点执行，不只本机。来源是控制端仓库的 `src/detect/manifests/pi.toml`（须 ≥ `2026.11.02.1`：独立状态行容忍行首缩进与尾缀，新增 `osc_title` 的 `:running...` 规则，边框嵌入形态不变）。远端不一定有这份仓库检出。目标 `~/.config/herdr/agent-detection/pi.toml`。已有覆盖时先 diff 比较合并，不直接覆盖。Windows 节点用 `terminal/pi.toml` 副本，步骤见 terminal/README.md。

本机没有覆盖，或覆盖版本低于仓库文件时复制；已有且内容不同则先 diff，不直接覆盖。然后重载本机每个运行中的会话服务器：

```bash
mkdir -p ~/.config/herdr/agent-detection
cp src/detect/manifests/pi.toml ~/.config/herdr/agent-detection/pi.toml
herdr --session work server reload-agent-manifests
```

远端同样先比较版本。没有覆盖或版本更低时，从控制端仓库拷文件，不要假设远端有这份检出。已有且内容不同则先 diff。重载必须打到该节点，不能在控制端执行不带 `--machine` 的 reload：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 "$target" 'mkdir -p ~/.config/herdr/agent-detection'
scp -o BatchMode=yes src/detect/manifests/pi.toml "$target:.config/herdr/agent-detection/pi.toml"
ssh -o BatchMode=yes -o ConnectTimeout=8 "$target" "herdr --session $session server reload-agent-manifests"
```

完成判据：该节点 `herdr --session "$session" server agent-manifests` 中 pi 的生效版本不低于仓库文件，来源是本地覆盖或已经达到该版本的发布清单。任务期间 `herdr agent explain <pane> --json` 返回 `state: working` 且 `matched_rule` 非 null（回退原因不再是 `default_known_agent_idle_fallback`）；任务结束回落 idle/done。当前没有正在执行的任务时，用带行首空格的 ` ⠴ Working` 样本跑 `herdr agent explain --file` 确认命中，不把空闲输入提示符当成检测失败。

移除条件：安装的 Herdr 发布版内置或远程 pi manifest ≥ `2026.11.02.1` 时，比较新规则后删除该覆盖并再次 reload。Windows 节点用 `terminal/pi.toml` 副本，步骤见 terminal/README.md。

### 2.4 Herdr Pi 集成（pi-ask 阻塞状态依赖）

对[同步目标](#同步目标)中每台运行 pi 的节点执行，不是仅控制端。本机直接运行；远端必须 SSH 到该节点，`herdr --machine` 不会转发安装：

```bash
herdr integration install pi && herdr integration status
ssh -o BatchMode=yes -o ConnectTimeout=8 "$target" 'herdr integration install pi && herdr integration status'
```

期望该节点输出 `pi: current`。

安装文件（`~/.pi/agent/extensions/herdr-agent-state.ts`）由 Herdr 管理，不手工修改。已有 pi 进程需在输入框执行 `/reload` 或重启会话；不要向正在跑的窗格注入 `/reload`，在结果里列出还没加载集成的节点。集成启用后该 pane 的状态以集成上报为准（`agent explain` 显示 `full_lifecycle_hook_authority`），屏幕规则作为无集成时的兜底。

完成判据：pi-ask 问答打开时该 pane 显示 blocked（红圈），提交/取消后恢复。

### 2.5 影响检测的 pi 包对照

pi 环境的包不随本仓库同步，但以下包直接改变屏幕/标题信号，与检测规则相关，同步 pi 环境时需一并存在：

| 包 | 对检测的影响 | 依赖的规则 |
|----|----|----|
| pi-powerline（替换编辑器） | working 指示不再嵌入边框，变为缩进独立行 | `working_border` / `working_literal` 的 `^\s*[⠋…] Working\b` |
| @tmustier/pi-tab-status | working 时 OSC 标题追加 `:running...` | `working_title` |
| jwu/pi-ask | 问答等待经事件总线报 blocked | Herdr Pi 集成（非屏幕规则） |
| Herdr Pi 集成（由 herdr 安装） | 生命周期上报接管屏幕检测 | `herdr integration install pi` |

### 2.6 Herdr UI（macOS 图形端，可选）

- 安装：官网 `https://herdrui.dev`（当前已验证版本 20261028.1，bundle id `so.pen.herdr-gpui`；无自动更新 feed，升级需按官网重新安装）。
- 字体：`brew install --cask font-fira-mono-nerd-font`，然后

```bash
/Applications/Herdr.app/Contents/MacOS/Herdr config set terminal.family "FiraMono Nerd Font Mono"
```

- 默认会话（图标启动即连 `work`）：

```bash
launchctl setenv HERDR_SESSION work
cp workflows/nantas/ui/local.herdr.gpui-session.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.herdr.gpui-session.plist
```

完成判据：`Herdr config check` 无问题；`launchctl getenv HERDR_SESSION` 返回 `work`；退出并从图标重开 Herdr.app 后 Local 显示 `work` 会话的工作区（非 `~`/default）。

副作用与回退：`launchctl setenv` 对之后启动的所有 GUI 应用生效（Dock 终端里的 `herdr` CLI 也会连 `work`）。回退执行：

```bash
launchctl bootout gui/$(id -u)/local.herdr.gpui-session
launchctl unsetenv HERDR_SESSION
rm ~/Library/LaunchAgents/local.herdr.gpui-session.plist
```

### 2.7 机器互连

`herdr machine add <SSH目标> --remote-session work --label <标签>`；地址与认证按新机器实际网络填写，不复制旧局域网值。完成判据：`herdr machine status <label>` 为 reachable，UI 侧边栏出现该机器并可切换。

## 3. 验证汇总

| 项 | 命令 / 判据 |
|----|----|
| 服务器 | `herdr status`、`herdr --session work status`（detached true） |
| 配置 | `herdr config check`、`herdr server reload-config` |
| 仓库工具 | `just nantas-presets-test`、`just nantas-git-test`、`shell/test_colors.py` |
| pi 检测 | 任务期间 `agent explain <pane> --json` → working + matched_rule |
| pi 集成 | `herdr integration status` → pi: current；问答 → blocked |
| Herdr UI | `Herdr config check`；图标启动连 work；`launchctl getenv HERDR_SESSION` |
| 互连 | `herdr machine status` → reachable |
| 局域网 | 每台已启用机器有 status；reachable 节点的 2.3 与 2.4 判据与本机相同 |

## 4. 不同步的内容（边界）

以下内容不随本仓库同步，留在各自执行节点：SSH 密钥与各类凭据；pi 的模型、授权与包配置（`~/.pi/agent` 中除 Herdr 集成文件外，由 pi-config / neonspark 机制另行管理）；Herdr UI 安装包本体；各节点备份；机器地址与外置盘路径。仓库文档不写入任何私钥、token 或完整个人配置内容。

仓库来源、且必须装在跑 pi 的节点上的文件要同步到每台可达的已保存机器：当前是 pi 检测覆盖和 Herdr Pi 集成。这不属于上面的私有配置。
