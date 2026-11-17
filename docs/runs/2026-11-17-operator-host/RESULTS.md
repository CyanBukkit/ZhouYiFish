# ZhouYiFish 人物沙盒真实接口实验记录

生成时间：2026-11-17T10:59:38+08:00（Asia/Shanghai，UTC+8）

## 结论

两个指定模型的短连通测试均未通过。向用户指定的 `http://m4.cyanbukkit.cn:3000/v1/chat/completions` 各发出 1 次请求，并按规则用同一参数重试 1 次；四次均得到 HTTP 500，延迟约 1–10 毫秒，没有可用的补全文本，也没有 usage。因此未进入「3 个人物 × 3 个场景 × 3 个臂」的对照调用。

- 对照成功次数：0
- 结构输出率：对照未跑，无法计算
- 各臂输出差异：无模型输出可比较
- 请求硬上限 60，实际使用 4，剩余 56；未跑对照项 54

本轮记录器没有把 500 响应体写入 JSONL，这是记录缺陷，因而不能从正文判断是服务端错误还是网关拦截页。在未再携带密钥发请求的前提下，额外观察到：`m4.cyanbukkit.cn` 解析到 `198.18.0.1:3000`，TCP 约 1 毫秒可连通，运行环境存在 `SAND_EGRESS_TUNNEL_PROXY_ADDR=127.0.0.1:8791` 与 `SAND_HTTP_PROXY_NAME=runner-egress-proxy`。这与本机或网关快速返回 500 相符，但不能在缺少响应体时定为唯一原因。按要求未改用 HTTPS、未更换服务、未绕过网关，并停止继续调用。

**没有真实行为标签，不计算准确率、Brier 分数或“提升”。模型输出不是 ground truth。核心结论：本次未能获得实验性人物输出，无法证明预测现实更准。**

## 输入来源

- 仓库：https://github.com/CyanBukkit/ZhouYiFish，分支 `main`
- 文件：`research/experiments/persona_sandbox_v1/result.json`，GitHub blob SHA `b8c041d2b3c1e6295b750c7dcaf96f0b4ddc2a16`
- 本地副本 SHA-256：`8c5c997bbe0efd1d1df3e442e4894e97c5b5a75d300f01ca9b75a40e27d6169f`
- narrow read of existing sandbox prompts; shuffled-arm text was not present as a ready-made field and is derived from the with_bazi template plus the frozen shuffle table
- 系统指令为本实验包装，不在仓库该输入文件的现成字段中；原文与哈希见 `inputs/prompts_manifest.json`。
- 打乱臂提示按附八字模板替换为冻结 shuffle 表中的八字。`sandbox-focal-01` 的冻结对为本人八字（`own_chart=true`），此人物的附八字臂与打乱臂八字相同。

## 调用设置

- 端点：`http://m4.cyanbukkit.cn:3000/v1/chat/completions`（用户指定的 HTTP 明文地址，未改用其它服务）
- 请求模型名：`mimo-v2.6-pro`, `gpt-6-astra`
- 服务返回的 model 字段不是独立身份核验，不能据此声称已核实官方型号。
- temperature=0，对照调用 max_tokens=512，连通测试 max_tokens=16
- timeout=90s，并发≤2，同一参数最多重试 1 次
- 请求硬上限 60，实际使用 4，剩余 56
- 未使用价格表，不报告金额；只记录服务返回的 token usage。
- 本实验是聊天补全对照，不是原版 MiroFish 群体仿真。

## 连通测试明细

| 请求序号 | 模型 | 尝试 | 重试自 | HTTP | 延迟(ms) | 开始时间（Asia/Shanghai） | 结果 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `mimo-v2.6-pro` | 1 | — | 500 | 10 | 2026-11-17T10:59:38+08:00 | HTTPError 500 |
| 2 | `mimo-v2.6-pro` | 2 | 1 | 500 | 1 | 2026-11-17T10:59:38+08:00 | HTTPError 500 |
| 3 | `gpt-6-astra` | 1 | — | 500 | 1 | 2026-11-17T10:59:38+08:00 | HTTPError 500 |
| 4 | `gpt-6-astra` | 2 | 3 | 500 | 1 | 2026-11-17T10:59:38+08:00 | HTTPError 500 |

服务未返回 model 字段或 usage。响应体本轮未保存。

## 总体计数

- 写入记录 4 条（含连通、对照、重试）
- 连通测试记录 4 条
- 对照请求记录 0 条
- 因硬上限跳过 0 条
- 未跑项 54 条

### 未跑项

- `mimo-v2.6-pro` / sandbox-focal-01 / without_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-01 / with_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-01 / shuffled_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-01 / without_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-01 / with_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-01 / shuffled_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-01 / without_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-01 / with_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-01 / shuffled_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-02 / without_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-02 / with_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-02 / shuffled_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-02 / without_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-02 / with_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-02 / shuffled_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-02 / without_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-02 / with_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-02 / shuffled_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-03 / without_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-03 / with_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-03 / shuffled_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-03 / without_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-03 / with_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-03 / shuffled_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-03 / without_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-03 / with_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `mimo-v2.6-pro` / sandbox-focal-03 / shuffled_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-01 / without_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-01 / with_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-01 / shuffled_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-01 / without_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-01 / with_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-01 / shuffled_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-01 / without_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-01 / with_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-01 / shuffled_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-02 / without_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-02 / with_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-02 / shuffled_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-02 / without_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-02 / with_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-02 / shuffled_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-02 / without_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-02 / with_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-02 / shuffled_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-03 / without_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-03 / with_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-03 / shuffled_bazi / 是否把一份共享备忘录交给同事继续改：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-03 / without_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-03 / with_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-03 / shuffled_bazi / 是否报名参加社区读书会：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-03 / without_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-03 / with_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run
- `gpt-6-astra` / sandbox-focal-03 / shuffled_bazi / 是否在小组会上说明自己的不同意见：connectivity_failed_or_not_run

## 模型 `mimo-v2.6-pro`

- 连通测试：未通过
- 未触发余额不足、封禁或不支持模型的停止条件。
- 该模型请求记录数：2（含连通与可能的重试）
- 对照题最新一次：0，其中 HTTP 成功且有文本：0
- 结构输出率（成功对照中可解析为 choice=cooperate/refuse 的 JSON）：无成功对照可计算
- usage（全部该模型记录合计，非金额）：prompt_tokens=0，completion_tokens=0，total_tokens=0，含 usage 的记录 0 条
- 成功对照延迟（毫秒）：n=0，min=None，mean=None，max=None
- 服务回报的 model 字段取值：无（这不是独立身份核验）
- 三臂均成功的人物×场景组数：0

## 模型 `gpt-6-astra`

- 连通测试：未通过
- 未触发余额不足、封禁或不支持模型的停止条件。
- 该模型请求记录数：2（含连通与可能的重试）
- 对照题最新一次：0，其中 HTTP 成功且有文本：0
- 结构输出率（成功对照中可解析为 choice=cooperate/refuse 的 JSON）：无成功对照可计算
- usage（全部该模型记录合计，非金额）：prompt_tokens=0，completion_tokens=0，total_tokens=0，含 usage 的记录 0 条
- 成功对照延迟（毫秒）：n=0，min=None，mean=None，max=None
- 服务回报的 model 字段取值：无（这不是独立身份核验）
- 三臂均成功的人物×场景组数：0

## 限制与复现

- 没有真实行为标签，本结果不是准确率、Brier 分数或提升证据。
- 模型输出不是 ground truth。
- 服务返回的 model 字段不是独立身份核验，不能据此声称 gpt-6-astra 或 mimo-v2.6-pro 已与官方型号核实。
- 未使用公开价格表，因此不报告金额，只报告 usage token 计数（若服务返回）。
- sandbox-focal-01 的冻结 shuffle 对为 own_chart=true，打乱臂与附八字臂使用相同八字；若提示文本因此相同，臂间差异不能归因于八字不同。
- 系统指令是本次实验包装，不在仓库 result.json 的现成字段中。
- 本实验是聊天补全对照，不是原版 MiroFish 群体仿真。
- 脱敏后的逐条输入输出见 `artifacts/raw_io.jsonl`，汇总见 `artifacts/summary.json`。
- 复现脚本：`run_live_test.py`（标准库即可）。将密钥放在本地私有 JSON（字段 `api_key`、`base_url`、`models`），不要把密钥写入仓库或本报告。
- 示例：`python3 run_live_test.py --config /path/to/private/api.json --input inputs/persona_sandbox_v1_result.json --out .`

