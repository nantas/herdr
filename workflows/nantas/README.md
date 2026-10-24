# nantas 的双机 Agent 工作流

本目录是本 fork 的个人工作流维护入口，不属于 Herdr 官方功能。脚本使用 Herdr CLI，不改动核心运行时。原始讨论留在本地 `.local/prd/`；可复用工具以本目录为准。

2026-10-22 原双机验证环境：Mac 与 Linux 均为 Herdr 0.9.5 stable、Codex CLI 0.163.0，Herdr 位于各自的 `~/.local/bin/`。需要 Python 3、SSH，以及 PATH 中的 `herdr` 和 `codex`。以下旧拓扑仅适用于对应局域网，不应直接复制到其他机器。

### Windows 控制端

WezTerm 右键与 pi 工作状态的本地修复见 [Windows 终端配置](terminal/README.md)，可复用配置保存在同目录；无需修改 Herdr 核心或重新编译。

启动器支持 Windows 的进程文件锁，Windows Python 还需要 `windows-curses`（已验证 Python 3.14 与 windows-curses 2.4.2）。安装 Herdr 时保留完整 Windows ZIP 中的 ConPTY 运行库。

将启动器保存到 `%USERPROFILE%\.config\herdr-project\herdr-project.py`，将本机专用的预设放到同目录 `presets.json`。通过 PATH 中的 `herdr-project.cmd` 调用实际 Python 路径及脚本，并转发 `%*`；不要依赖 Windows Store 的 Python 别名。Windows Herdr 配置在 `%APPDATA%\herdr\config.toml`，项目弹窗命令使用 PATH 中的 `herdr-project --pick`，其余字段沿用 `presets/picker.toml`。

本机预设使用 `session: work` 和 Windows 绝对目录；远端预设使用已保存的 `machine` 标签和远端绝对目录。远端目录若为符号链接，先通过 SSH 在目标目录执行 `pwd -P`，保存实际路径，以便与 Herdr 返回的前台目录匹配。每台控制端独立维护预设、状态与锁，不复制旧局域网配置或 `state.json`。

用 `herdr machine add <SSH别名> --label <标签> --remote-session work` 保存远端，再运行 `herdr session attach work` 打开聚合界面。在 Local 按 `Ctrl+B` 后按 `Alt+P` 选择项目；远端项目准备完成后关闭提示，再从侧边栏选择该机器。命令行也可执行 `herdr-project <预设名>`；已有界面时用 `--no-attach`。

直接打开 SSH 界面时，要使用远端扩展快捷键，需加 `--remote-keybindings server`。项目启动器的远端 attach 已自动加此参数；手工连接例如 `herdr --remote mac-pi --session work --remote-keybindings server`。未加该参数时，0.9.5 的直接 SSH 客户端不提供远端自定义命令，不能据此判断远端工具没有安装。

当前 Windows/mac-pi 已部署 `Ctrl+B` 后 `Alt+G` 的 Git 文件列表。Windows 使用 `herdr-git-status.cmd` 调用 Python（`-X utf8`）与已安装脚本，Mac 使用 `~/.local/bin/herdr-git-status`。Windows 快照缺少 `foreground_cwd` 时，工具通过 `pane process-info --pane` 查询实时前台进程；只有所有前台进程提供一致目录时才继续，绝不使用旧 `cwd` 静默回退。PDCurses 使用原生键盘/鼠标事件，macOS 保留 SGR 序列解析。

2026-10-22 配置迁移验证：两端配置检查与 reload 成功；Windows 临时会话验证切换目录后的 Git 定位、双向滚轮、End、刷新、关闭及项目选择器打开/取消；Windows 经 SSH 在 Mac 临时会话验证远端 Git 目录、双向滚轮、End 和三个 Mac 项目的选择器。Windows Git 测试 9 项、项目启动器/选择器 18 项、Pi 补全路由 8 项通过；Mac Git 测试 9 项通过。没有重启原 `work` 或提交模型任务。测试命令使用 Python/Bun（当前机器未安装 `just`）。

当前 Windows 的用户级 Windows PowerShell profile 与 Mac `.zshrc` 已加入交互终端颜色处理，只在 `HERDR_ENV=1` 时清除 `NO_COLOR`；新 shell 生效，已有 Agent 环境不变。两端 Pi 均安装 GitHub 自动补全扩展，并以无模型请求的 RPC 启动验证加载：Windows 引用本 checkout 的 `.pi/extensions/github-issues-autocomplete`，Mac 使用 `~/.local/share/herdr-tools/github-issues-autocomplete` 副本。Pi 扩展提供 `@issue` / `@pr` 补全，不改变 Codex。旧 Mac→Linux 的私有配置同步 skill 经用户决定暂不迁移。

2026-10-22 Windows 验证：Herdr 0.9.5、Codex 0.163.0；五个本机/远端预设启动及再次选择复用成功，terminal ID 保持不变；真实 Windows 终端选择器打开/取消，以及 Herdr 内弹窗选择本机项目后退出并聚焦通过。未提交模型任务。未配置休眠策略。

当前 Windows/mac-pi 环境已按用户选择配置**登录后**自动启动 `work` 服务器，不是无人登录时启动：

- Windows：任务计划程序的 `Herdr work server`，当前用户、普通权限、登录触发；无运行时限，电池供电不停止，忽略重复启动。启动脚本在 `%LOCALAPPDATA%\herdr\autostart\work-server.ps1`，通过安装器的 `current\herdr.exe` 路径运行隐藏服务器；标准输出与错误分别写入同目录日志，避免 Windows PowerShell 将原生命令的正常 stderr 当作终止错误。服务器由任务计划服务托管，不依赖创建它的终端或 Agent 会话。
- mac-pi：`~/Library/LaunchAgents/local.herdr.work.plist`，`RunAtLoad` 通过 `/usr/bin/python3 ~/.config/herdr/autostart/session-server.py ~/.local/bin/herdr --session work server` 启动，由当前用户的 launchd GUI 域托管；包装脚本源为 [session-server.py](presets/session-server.py)，以 `start_new_session=True` 创建服务器、等待退出并转发终止信号。日志在 `~/.config/herdr/autostart/`。注销用户后不保证继续运行，下次登录重新启动。

直接由 launchd 启动的进程可能只有进程组 ID 等于 PID，而 Unix 会话 ID 不等于 PID。Herdr 0.9.5 会因此报告 `detached_server_daemon: false` 并在直接 SSH attach 时建议重启。上述包装脚本使服务器的会话 ID 等于 PID，同时保留 launchd 托管。已实测返回 `detached_server_daemon: true`，Windows 直接 SSH attach 不再提示重启，分离客户端后服务器继续运行。外置盘授权经用户允许后，在新启动方式下仍有效，三个远端 Codex 已重新启动；Codex 自身的 hook 信任提示由用户决定，不自动批准。

已通过任务计划启动及 launchd bootstrap 验证两端服务器可达，并核对 Windows 的服务进程祖先及 Mac 的 PID 1 父进程；未执行整机重启验收。自启动仅启动 Herdr 服务器，不保证恢复原 Codex 对话。此次服务器重启恢复了项目目录和窗格，但 terminal ID 更新且没有自动恢复 Agent；人工核对唯一匹配的空窗格、备份并更新控制端映射后，Windows 两个项目与 Mac 内置盘项目重新启动成功。Mac 外置盘项目在 launchd 上下文中触发系统 TCC 卷访问请求，需要用户在桌面完成授权后再验证；不能把 SSH 上下文可访问外置盘视为 launchd 已获授权。不要在将来的重启后直接假设旧 `state.json` 仍指向有效实例。

## 节点与会话

Mac 是控制端，也运行本地 Agent。Linux 通过 SSH `nantas@10.23.5.117` 连接，保存为机器配置 `linux-work`。两台机器各有独立的 `work` 会话及服务端，进程在各自机器执行。

首次配置需要在两端安装兼容版本的 Herdr、配置 Codex 登录，并确认 SSH 密钥及 known_hosts 已就绪。在 Mac 中保存远端配置一次：

```bash
herdr machine add nantas@10.23.5.117 --label linux-work --remote-session work
herdr session attach work
```

已有 `linux-work` 时复用，不重复添加。统一界面从侧边栏选择 Local 或 linux-work。裸 `herdr` 使用默认会话，不能代替 `herdr session attach work`。

仅打开远端界面：

```bash
herdr --remote nantas@10.23.5.117 --session work
```

## 固定目录 + Codex 快捷入口

[presets/presets.json](presets/presets.json) 保存四个固定组合：

| 入口 | 节点 | 工作目录 |
| --- | --- | --- |
| neonspark-mac | Mac / work | /Volumes/Shuttle/unity-projects/neonspark |
| neonspark-linux | linux-work / work | /home/nantas/data/projects/neonspark |
| neonnew-mac | Mac / work | /Users/nantasmac/projects/neonnew |
| neondesign-mac | Mac / work | /Volumes/Shuttle/unity-projects/neondesign |

从本仓库根目录安装命令。配置已存在时先比较并合并需要的条目，以下 `cp -n` 保留原配置：

```bash
mkdir -p "$HOME/.local/bin" "$HOME/.config/herdr-project"
install -m 755 workflows/nantas/presets/herdr-project.py "$HOME/.local/bin/herdr-project"
cp -n workflows/nantas/presets/presets.json "$HOME/.config/herdr-project/presets.json"
herdr-project
```

普通终端运行以下任一命令，准备 Agent 并打开界面：

```bash
herdr-project neonspark-mac
herdr-project neonspark-linux
herdr-project neonnew-mac
herdr-project neondesign-mac
```

已有 Herdr 界面时，在 **shell 窗格**执行，避免输入到 Codex 对话框：

```bash
herdr-project neonnew-mac --no-attach
```

`--no-attach` 只创建或复用并聚焦目标，不打开新客户端，也可在外部终端使用。Herdr 内忘加时，脚本依据 `HERDR_ENV=1` 拒绝嵌套启动。远端入口不带此参数时打开远端独立界面；需要聚合界面时加此参数，然后在已有界面选择 linux-work。

### 项目选择弹窗（Mac Local）

安装上述启动器后，将 [picker.toml](presets/picker.toml) 的 `[[keys.command]]`
条目合并到 Mac 的 `~/.config/herdr/config.toml`，先备份配置并核对快捷键冲突。
保留现有表和命令，只添加该条目；不要用片段覆盖整份配置。

```bash
herdr config check
herdr --session work server reload-config
```

在 Herdr 的 **Local** 界面按 `Ctrl+B`，再按 `Alt+P` 打开弹窗。
选择器直接读取 `~/.config/herdr-project/presets.json`，显示名称、执行节点、Agent 和目录。
用上下键或 `j/k` 选择，鼠标点选／滚轮也可改变选择；Enter 启动，Esc 或 `q` 取消。
本地成功后弹窗自动退出并聚焦目标；远端结果或错误停留在弹窗，按 Enter、Esc 或 `q` 关闭。
也可在普通交互终端运行 `herdr-project --pick`。

选择后调用同一个启动器的 `--no-attach` 路径，保留实例复用、锁和歧义检查。
Local 项目会聚焦对应工作区；远端成功后提示选择 `linux-work`（或预设指定的机器），
需手动切换侧边栏机器。启动等待期间不要重复提交；若超时或失败，先检查目标状态再重试。
旧格式不变，不复制项目清单，不修改 `state.json` 的含义。

首版仅在 Mac 控制端的 Local 使用；快捷键不会替远端安装启动器。
修改配置只需 reload，无需停止 `work` 或现有 Agent。卸载时只移除该自定义命令条目并 reload。
验证：`just nantas-presets-test`。

2026-10-22：Mac 启动器和快捷键已安装，配置检查和 `work` reload 成功，原有四个 terminal
身份保持不变。Herdr 0.9.5 隔离会话实测弹窗打开、取消、Codex 0.163.0 启动、重复选择
复用同一 terminal，以及成功后再次打开弹窗；未发送模型任务，临时会话已清理。
用户已在当前 Herdr 窗口手动验证通过。远端提示通过测试，尚未通过新弹窗实测 Linux 启动。配置和旧启动器备份保留在 Mac 的
`~/.config/herdr/local-backups/`，不进入仓库。

### 交互终端颜色

启动器清除自身传给 Herdr 的 `NO_COLOR`，新建工作区时还通过 `--env NO_COLOR=`
覆盖运行中服务端继承的禁色设置。已验证 Codex 0.163.0 将空值视为允许颜色。
本地和远端新建工作区都使用此覆盖，无需重启 `work` 或重新构建 Herdr。

手工启动路径由 [交互 shell 片段](shell/interactive-colors.sh) 覆盖：Mac 和 Linux 均已安装到
`~/.config/herdr/interactive-colors.sh`，并由各自 `~/.zshrc` 加载。仅当 shell 是交互式且
`HERDR_ENV=1` 时清除 `NO_COLOR`；普通终端和非交互命令保留其原设置。
以后在 Herdr 手工新建窗格，再直接运行 `codex`，也会使用清理后的环境。

在其他节点安装时，复制此片段到上述路径，并在该节点 `.zshrc` 末尾添加一次：

```sh
# nantas Herdr interactive colors
[ ! -r "$HOME/.config/herdr/interactive-colors.sh" ] || . "$HOME/.config/herdr/interactive-colors.sh"
```

安装前先备份原 `.zshrc`；现有两端备份保留在各节点
`~/.config/herdr/shell-backups/`，不复制回仓库。卸载时移除这两行及片段文件。
验证：`python3 workflows/nantas/shell/test_colors.py`。
已用两端真实 `zsh -lic` 启动验证：Herdr 环境清除变量，普通环境保留变量。

已有工作区及 Agent 的环境不会被修改。旧实例如无颜色，等任务结束后退出 Codex，
在该窗格的 **shell 提示符**中执行以下命令，并选择原会话：

```sh
unset NO_COLOR
codex resume
```

这会清除当前 shell 的变量，之后从同一个 shell 普通启动 Codex 也会允许颜色。
`env -u NO_COLOR codex resume` 也可恢复颜色，但只对该次启动有效，不改变父 shell。
重新 attach 或 reload config 不会改变旧进程的环境；无需停止整个 `work`。

2026-10-22 安装状态：Mac 与 Linux 的 zsh 启动适配均已部署；两端真实 shell
环境对照验证及本地回归测试通过。未重启现有 Agent，未完成新远端 Agent 的颜色端到端验证。
若要回退，优先只删除上述加载片段，避免恢复整份旧 `.zshrc` 时覆盖安装后的其他修改。


### 复用与上下文

- 根据实际前台目录和 Agent 类型匹配，不依赖工作区标签。实例已经转到别的项目时保留原实例，另建目标项目实例。
- 优先复用本机 `~/.config/herdr-project/state.json` 记录的 terminal ID；否则复用唯一匹配实例。多个匹配时优先唯一聚焦实例，仍不明确则报错。
- 没有实例才创建工作区及 Codex。启动失败保留映射，避免重试重复创建工作区。
- `args` 为空，继承节点现有 Codex 设置；修改参数仅影响以后新启动的 Agent。
- Agent 使用执行节点项目的 AGENTS.md 与 skills。Herdr 不替换项目 harness；新实例开启新的原生 Agent 会话，不自动恢复历史对话。
- 不同终端连接同一节点的 `work` 时共享进程，不是各自启动一套 Agent。避免多个客户端同时向同一 Agent 输入。
- 本机锁防止同一控制端并发重复创建；未来多个控制端同时创建的分布式互斥尚未实现。

启动入口要求目标 `work` 服务端已运行；若停止，先用前述 attach 命令启动。`state.json` 和 `launch.lock` 是节点本地运行文件，不复制到其他机器、不提交 Git。

## 分离、关闭与停止

`Ctrl+B` 后按 `q` 分离客户端，服务端与 Agent 继续运行。重新 attach 可继续使用原进程和上下文。执行机器必须持续运行；尚未配置开机启动或休眠策略。

在界面关闭工作区会结束其中由 Herdr 管理的终端和 Agent。也可先查询实际目录，再按当前工作区 ID 关闭；不要保存或照抄历史 w1/w2 等 ID：

```bash
herdr --session work workspace list
herdr --session work pane list
herdr --session work workspace close <workspace_id>
```

工作区标签可能落后于实际目录。例如此前名为 neonspark 的工作区后来切换到了 neonnew，不能只凭标签清理。

以下为停止操作，会结束相应会话所有工作区的运行进程：

```bash
herdr session stop work                    # 本机
herdr --machine linux-work server stop     # Linux
```

需要进一步删除本机已停止会话的保存数据时，执行 `herdr session delete work`。这些操作不删除项目源码或快捷入口配置。独立后台服务、Docker 容器等可能需要另行停止；服务端重启后的进程和上下文恢复不在已验证范围内。

连接异常先检查，避免把停止服务端当作重连：

```bash
herdr --session work status server
herdr machine status linux-work --json
herdr --machine linux-work status server
```

`--machine linux-work` 已绑定远端会话，不与 `--session` 混用。CLI 的目标由命令参数决定，与界面当前选中的机器无关。

## Git 变更文件弹窗

[herdr-git-status.py](git/herdr-git-status.py) 在选中节点上只读查询当前 pane 的实际前台目录，
再由 Git 定位所属 worktree。目录不可用、非 Git 目录或查询失败时显示错误，不回退到
启动目录或 Mac 上的同名路径。`r` 刷新会重新查询实际目录；干净工作区显示明确提示。

Mac 和 Linux 各安装同一脚本到 `~/.local/bin/herdr-git-status`，需要 Python 3（含 curses）
和 Git。在各节点能访问源码的位置执行：

```bash
install -m 755 workflows/nantas/git/herdr-git-status.py "$HOME/.local/bin/herdr-git-status"
```

将 [popup.toml](git/popup.toml) 条目分别合并到两端 `~/.config/herdr/config.toml`，
先备份并检查快捷键冲突，保留已有设置。文件不存在时可用此片段新建。
每个节点执行 `herdr config check` 和 `herdr --session work server reload-config`；
从 Mac 也可用 `herdr --machine linux-work server reload-config` 重载远端。
工具和配置各自部署，Herdr 不会自动复制它们。

在 Local 或 linux-work 的目标 pane 上，按 `Ctrl+B` 再按 `Alt+G` 打开。
弹窗在当前客户端显示，但脚本、pane 查询和 Git 命令都在选中服务端运行。

- 滚轮、上下键或 `j/k` 滚动，PageUp/PageDown 翻页，Home/End 到首尾。
- 左右键横向浏览长文件名；Home 同时复位横向偏移。
- `r` 刷新；Esc 或 `q` 关闭并返回原 pane。
- 前两列分别表示暂存区和工作区的状态，空格表示该列没有变更。`M ` 表示已暂存修改，
  ` M` 表示未暂存修改，`MM` 表示两者都有；`A` 新增、`D` 删除、`R` 重命名，
  `??` 表示未跟踪。重命名显示旧名 → 新名，制表符、换行等文件名字符以转义形式展示。

首版只展示文件列表，不查看完整 diff、不暂存、不提交。Git 查询禁用可选 index 锁写入。
测试：`just nantas-git-test`，使用临时仓库覆盖普通及 linked worktree、各类变更、重命名、
特殊文件名、失败和滚动刷新。Mac 系统 curses 缺少向下滚轮常量，工具直接解析标准 SGR
鼠标序列，两端不需要额外 Python 包。

2026-10-22：两端工具及快捷键均已部署并 reload；Mac 原有 4 个和 Linux 原有 2 个 terminal
身份保持不变。Herdr 0.9.5 的两端隔离会话验证了弹窗、双向滚轮、关闭后的 pane/焦点恢复；
Mac 另实测刷新到新增文件并滚到列表末尾，SSH 客户端实测显示 Linux 临时仓库，未查询 Mac 路径。
临时会话均已停止并删除。用户已在当前窗口手动验收，并确认修正后的列说明和状态图例。
未操作实际项目 Git 状态，未启动或重启现有 Agent。

备份只在各节点 `~/.config/herdr/local-backups/`。Linux 原先没有 config.toml，备份目录以
`config-was-absent` 记录；回退时移除本快捷键和工具并 reload，保留安装后新增的其他配置。

## neonspark 私有配置同步

[neonspark-local-config skill](skills/neonspark-local-config/SKILL.md) 是项目级工作流入口。由 Mac 主动经 SSH 推送 Linux，无需反向连接或中心配置服务。只处理以下相对路径：

- `Backend/CloudBase/.env.local.dev`
- `Backend/CloudBase/.env.local.prod`
- `.local/taptap-harden.json`
- `.agents/skills/fetch-codecks-bug/.local.env`

Mac 为来源。Linux 已有文件先备份再覆盖，无变化则保留；不根据 Git 状态扩展清单，不自动合并、不提交配置、不触发部署。清单适用于未跟踪文件，也可包含跟踪后仅作本地修改的文件；后者仍需人工避免把私有修改提交 Git。

### 安装或更新项目 skill

维护源是本目录 `skills/neonspark-local-config/`。复制其中的 `SKILL.md`、`scripts/sync.py`、`scripts/test_sync.py` 到两端对应项目的 `.agents/skills/neonspark-local-config/`，保持相同相对结构。安装前核对现有副本差异，仅覆盖这些工具文件。

在各项目的 `.git/info/exclude` 添加一行 `/.agents/skills/neonspark-local-config/`，使个人入口不进入项目提交。确认 `.local/neonspark-config-backups/` 与私有配置文件不会意外进入提交。不要复制私有文件内容、备份或运行状态到本仓库。同步脚本内 SOURCE、TARGET、HOST 为本工作环境的固定值；迁移环境时先核对再安装。

新项目 Codex 会话可发现此 skill；已运行会话若缓存旧列表，直接读取安装后的 SKILL.md，无需打断任务。Linux 上需要配置时，该入口指引用户从 Mac 推送。

在 Mac 的 neonspark Agent 中说“同步 neonspark 本地配置到 Linux”，或显式调用 `$neonspark-local-config`。手动入口：

```bash
python3 /Volumes/Shuttle/unity-projects/neonspark/.agents/skills/neonspark-local-config/scripts/sync.py --check
python3 /Volumes/Shuttle/unity-projects/neonspark/.agents/skills/neonspark-local-config/scripts/sync.py --apply
```

SSH 通过 stdin 传输配置，不把内容放入参数或日志；`--check` 也会传送数据用于比较，但不写目标。恢复步骤和备份规则见 skill。写入失败会尝试回滚，断电或强制终止不保证四文件整体原子性；备份本身也包含敏感信息。

## 验证与边界

在仓库根目录运行独立测试，不启动真实 Agent、不传送真实配置：

```bash
python3 workflows/nantas/presets/test_presets.py
python3 workflows/nantas/skills/neonspark-local-config/scripts/test_sync.py
```

此前实测：两端 neonspark 启动与重复复用、进入及分离 TUI、原进程上下文继续、项目 harness 可见；隔离 SSH 桥接中断后远端测试进程仍在，重连保持同一 terminal 和 PID。四个私有配置首次推送验证一致，用户确认生效。neonnew/neondesign 新预设已验证配置与目录，尚未单独实测启动。

未验证 VPN/物理网络黑洞、跨控制端并发创建、机器或服务端重启恢复、配置在实际部署工具中的业务有效性。Herdr 0.9.5 远端分离偶尔打印 Connection reset by peer，但此前观察服务端进程保持运行。

后续可讨论更细的 Agent 参数、测试/日志启动与布局；自动调度、开发/验证双角色流程、家庭 VPN 接入当前均未实施。
