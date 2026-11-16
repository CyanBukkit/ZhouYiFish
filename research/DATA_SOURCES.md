# 数据、规则与许可

## 规则转录

- 文献：《梅花易数》卷一
- 地址：<https://zh.wikisource.org/zh-hans/梅花易數/卷一>
- 性质：维基文库公开转录，不是校勘定本
- 本仓库核过的内容：卦以八除、爻以六除、年月日时起例，以及观梅占里的 34、43、兑、离、初爻、泽火革
- 没有核成定本的内容：作者是不是邵雍。页面里的「康节先生」只是转录中的叙述
- 使用范围：只实现年月日时的计数、先天卦数和一爻翻转。不把断语当成标签

## 农历

- 运行库：zhdate 0.1，GPL-3.0-or-later，<https://github.com/CutePandaSh/zhdate>
- 它自带 1900–2100 的月表和春节日期。本仓库没有另写一套农历
- 核对来源：香港天文台公历与农历对照表
  - <https://www.hko.gov.hk/en/gts/time/calendar/text/files/T2020e.txt>
  - <https://www.hko.gov.hk/en/gts/time/calendar/text/files/T2022e.txt>
  - <https://www.hko.gov.hk/en/gts/time/calendar/text/files/T2023e.txt>
  - <https://www.hko.gov.hk/en/gts/time/calendar/text/files/T2024e.txt>
  - <https://www.hko.gov.hk/en/gts/time/calendar/text/files/T2026e.txt>
- 核对过的边界写在 `research/tests/test_calendar.py`。闰月按对照表里同一月名的第二次出现
- 时区用 Python `zoneinfo` 的 `Asia/Shanghai`，保存每次的实际 UTC 偏移

## 天气结算

- 来源：Open-Meteo Historical Weather API
- 端点：`https://archive-api.open-meteo.com/v1/archive`
- 变量：`daily=precipitation_sum`，单位毫米，`timezone=Asia/Shanghai`
- 许可：CC BY 4.0，<https://creativecommons.org/licenses/by/4.0/>
- 署名：Weather data by Open-Meteo.com，<https://open-meteo.com/>
- 请求坐标：31.2304N, 121.4737E，上海人民广场附近的公开坐标，不是个人住址
- 实际网格以冻结快照里返回的坐标为准
- 快照写入之后不再改写。缺测保持空值

## 不使用的数据

不读取个人账户、私人消息或任何可识别个人的记录。
不把密钥、`.env` 或模型账单写进仓库。
