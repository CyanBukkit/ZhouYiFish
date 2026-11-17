# 实验产出

`offline_v1/` 是 2022–2023 的回顾性快照和评分。`future_ledger.jsonl` 保留原字节作审计，并被 `future_ledger_disposition.json` 标为 invalid/excluded。不要把那 30 行再放进前瞻队列。

`prospective_v2/` 是从 2026-11-18 起的内容锁。`ledger.jsonl` 只保存内容哈希。`public_anchor.json` 引用 GitHub 上引入该锁的提交时间。`eligibility.jsonl` 是用该时间比较出来的结果。结算只追加到 `settlement.jsonl`。

`verify-offline` 重算回顾性预测和说明，并核对旧台账字节没有被改写。它不调用模型。

`persona_sandbox_v1/` 是离线人物输入。2026-11-17 的用户电脑探针使用了其中的冻结 prompt，但 54 项对照没有跑成；记录在 [docs/runs/2026-11-17/README.md](../../docs/runs/2026-11-17/README.md)。`sandbox-focal-01` 的打乱对是自配对，限制写在 [SHUFFLE_LIMIT.md](persona_sandbox_v1/SHUFFLE_LIMIT.md)，该 `result.json` 不回改。
