# 离线实验产出

`offline_v1/` 在执行 `python3 -m research.cli run-offline` 之后才会出现。
其中的 Open-Meteo 快照是这次回顾性结算的唯一来源。
`verify-offline` 用这份快照重算并核对，不会重新下载，也不会调用模型。

前瞻台账在 `future_ledger.jsonl`。那些日期的结局必须保持空白。
