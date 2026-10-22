---
name: neonspark-local-config
description: neonspark 本地配置同步入口。当用户要求从 Mac 同步私有配置到 Linux，或 CloudBase、TapTap 加固、Codecks 工作流缺少本地配置时使用。仅覆盖已登记的四个文件，不执行部署。
---

# neonspark 本地配置

Mac 是来源，Linux 是目标。文件清单、路径和 SSH 目标由 `scripts/sync.py` 定义。
本入口安装在两端 neonspark 的 `.agents/skills/neonspark-local-config/`，可在 Herdr 中启动的 Codex 使用，也可用于直接启动的项目 Codex。

## 从 Mac 推送

用户要求同步时，在 Mac 执行；已有明确同步授权时无需重复询问：

```bash
python3 /Volumes/Shuttle/unity-projects/neonspark/.agents/skills/neonspark-local-config/scripts/sync.py --check
python3 /Volumes/Shuttle/unity-projects/neonspark/.agents/skills/neonspark-local-config/scripts/sync.py --apply
```

仅发现配置缺失、但用户未要求传输时，先说明此入口，由用户决定何时推送。
`--check` 比较四个文件，输出 create/replace/unchanged，不修改目标；配置通过 SSH stdin 传送，不进入命令参数或输出。
`--apply` 先备份全部将被替换的旧文件，再逐文件原子替换并校验。未变化的文件保留不动。
文件按原始字节传输，不解析、合并或执行内容。现有文件采用 Mac 版本；如用户要求例外合并，先定义该文件的规则再修改工具。

## 在 Linux 需要配置时

目标项目为 `/home/nantas/data/projects/neonspark`。告知用户：在 Mac 的 neonspark Agent 中说“同步 neonspark 本地配置到 Linux”，即可使用上述入口。
Linux 不连接 Mac，不尝试从其他项目猜测来源。配置到位后继续原任务；同步成功本身不授权任何开发或生产部署。

## 输出与恢复

报告文件相对路径、操作结果和备份目录。敏感文件内容留在文件和 SSH 数据流中；不使用 cat、diff、shell tracing 或把内容放入提示词/日志。
成功要求退出码 0、`verified: true`。失败时读取工具给出的状态；不得把部分完成当成功。

Linux 备份位于项目 `.local/neonspark-config-backups/<批次>/`；目录权限 700，文件 600，不进入 Git。`manifest.json` 记录原文件是否存在及原权限，`original/` 保留旧文件原始字节。备份包含敏感值，保留在节点本地，不提交或上传。
普通写入/校验失败会尝试回滚；输出 `rollback_failed` 时停止并按 manifest 和 original 人工恢复。异常断电/强制终止不保证四文件整体原子性，可依据备份恢复；无旧文件的条目没有旧副本。

## 会话发现

新启动的项目 Codex 可发现该 skill。已运行的会话若未刷新技能列表，先读取本 SKILL.md；不要重启正在执行任务的 Agent。不要以缺少全局系统提示注入为由改写仓库 AGENTS.md。
