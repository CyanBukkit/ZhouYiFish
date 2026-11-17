# 用户电脑双模型探针：归档说明

本目录是用户电脑上一次真实调用的脱敏产物，按收到的字节保存。本仓库提交没有再向接口发请求，也没有补写 500 响应体。

| 文件 | 内容 |
| --- | --- |
| [RESULTS.md](RESULTS.md) | 操作者写的实验记录 |
| [summary.json](summary.json) | 同一轮汇总 |
| [raw_io.jsonl](raw_io.jsonl) | 四条连通记录。操作者原文里的 `artifacts/raw_io.jsonl`、`artifacts/summary.json` 指的就是这两个文件 |

操作者提到记录脚本后来有修改，但没有用修改后的脚本补请求。那些脚本、`inputs/prompts_manifest.json` 和 500 响应体都不在交来的文件里，这里不补造。

## 测到的事实

- 来源是 main 上 `research/experiments/persona_sandbox_v1/result.json`。本提交未改该文件。其 SHA-256 仍是 `8c5c997bbe0efd1d1df3e442e4894e97c5b5a75d300f01ca9b75a40e27d6169f`，Git blob 仍是 `b8c041d2b3c1e6295b750c7dcaf96f0b4ddc2a16`。
- 端点按用户指定使用 `http://m4.cyanbukkit.cn:3000/v1/chat/completions`。请求模型名是 `mimo-v2.6-pro` 与 `gpt-6-astra`。
- 每个模型 1 次短探针加同一参数重试 1 次，共 4 次。HTTP 状态都是 500，延迟分别是 10、1、1、1 毫秒。没有 completion，没有 usage。
- 3 人 × 3 场景 × 3 臂 × 2 模型共 54 项全部未跑，原因记为 `connectivity_failed_or_not_run`。
- 这是聊天补全对照的输入准备，不是前端端到端，也不是原版 MiroFish / OASIS。
- 没有真实行为标签，没有准确率、Brier 或提升。模型能力与预测精度都未评估。

`summary.json` 里的 `core_conclusion` 是实验范围的预写句子，不是这次测到了可用输出。测到的结果在 `connectivity_outcome` 和 `comparison_calls: 0`。

## 不能从这次记录推出的事

记录器没有保存 500 响应体，所以不能判断错误来自远端服务还是当时那台电脑前面的网关。`summary.json` 里的 DNS 与出口代理观察只属于发出这四次请求的那台电脑。它不能用来宣称该接口对其它客户端不可用。

`sandbox-focal-01` 在冻结打乱表中 `own_chart` 为 true。该人物的打乱臂与附八字臂使用同一八字。限制说明见 [../../../research/experiments/persona_sandbox_v1/SHUFFLE_LIMIT.md](../../../research/experiments/persona_sandbox_v1/SHUFFLE_LIMIT.md)。这次没有改那张表。
