# 新机器初始化与本机配置同步

本页是 agent 在新机器（或需要重新同步的机器）上部署本 fork 个人工作流的唯一入口。逐节执行到"完成判据"即停；按机器矩阵跳过不适用的步骤。细节回到对应功能文档，本页不重复其内容，只维护顺序、来源与判据。

机器特定数据（SSH 目标、局域网地址、外置盘路径）不随本页复制，按 README 的[节点与会话](README.md#节点与会话)在新机器上现查现填。

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

### 2.3 pi 工作状态检测覆盖（macOS 节点）

来源：仓库 `src/detect/manifests/pi.toml`（须 ≥ `2026.11.02.1`：独立状态行容忍行首缩进与尾缀，新增 `osc_title` 的 `:running...` 规则，边框嵌入形态不变）。目标 `~/.config/herdr/agent-detection/pi.toml`。已有覆盖时先 diff 比较合并，不直接覆盖。

```bash
mkdir -p ~/.config/herdr/agent-detection
cp src/detect/manifests/pi.toml ~/.config/herdr/agent-detection/pi.toml
herdr server reload-agent-manifests          # 对每个运行中的会话服务器各执行一次
```

完成判据：pi 执行任务期间 `herdr agent explain <pane> --json` 返回 `state: working` 且 `matched_rule` 非 null（回退原因不再是 `default_known_agent_idle_fallback`）；任务结束回落 idle/done。

移除条件：安装的 Herdr 发布版内置或远程 pi manifest ≥ `2026.11.02.1` 时，比较新规则后删除该覆盖并再次 reload。Windows 节点用 `terminal/pi.toml` 副本，步骤见 terminal/README.md。

### 2.4 Herdr Pi 集成（pi-ask 阻塞状态依赖）

在**运行 pi 的节点**执行（不是仅控制端）：

```bash
herdr integration install pi && herdr integration status   # 期望 pi: current
```

安装文件（`~/.pi/agent/extensions/herdr-agent-state.ts`）由 Herdr 管理，不手工修改。已有 pi 进程需在输入框执行 `/reload` 或重启会话。集成启用后该 pane 的状态以集成上报为准（`agent explain` 显示 `full_lifecycle_hook_authority`），屏幕规则作为无集成时的兜底。

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

## 4. 不同步的内容（边界）

以下内容不随本仓库同步，留在各自执行节点：SSH 密钥与各类凭据；pi 的模型、授权与包配置（`~/.pi/agent` 中除 Herdr 集成文件外，由 pi-config / neonspark 机制另行管理）；Herdr UI 安装包本体；各节点备份；机器地址与外置盘路径。仓库文档不写入任何私钥、token 或完整个人配置内容。
