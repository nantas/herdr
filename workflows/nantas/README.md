# nantas 的双机 Agent 工作流

本目录是本 fork 的个人工作流维护入口，不属于 Herdr 官方功能。脚本使用 Herdr CLI，不改动核心运行时。原始讨论留在本地 `.local/prd/`；可复用工具以本目录为准。

2026-10-22 验证环境：Mac 与 Linux 均为 Herdr 0.9.5 stable、Codex CLI 0.163.0，Herdr 位于各自的 `~/.local/bin/`。需要 Python 3、SSH，以及 PATH 中的 `herdr` 和 `codex`。脚本使用 Unix 文件锁，未支持 Windows。

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
