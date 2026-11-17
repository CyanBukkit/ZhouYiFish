# 已冻结打乱表的自配对

`result.json` 里的 shuffle 已经用于 2026-11-17 的用户电脑探针输入，字节保持不动。SHA-256 为 `8c5c997bbe0efd1d1df3e442e4894e97c5b5a75d300f01ca9b75a40e27d6169f`。

三对之中：

| background_of | chart_from | own_chart | pillars |
| --- | --- | --- | --- |
| sandbox-focal-01 | sandbox-focal-01 | true | 辛巳甲午己酉己巳 |
| sandbox-focal-02 | sandbox-focal-03 | false | 戊辰壬戌辛酉丙申 |
| sandbox-focal-03 | sandbox-focal-02 | false | 辛未辛丑癸未丁巳 |

`sandbox-focal-01` 的打乱臂使用本人八字，因此可能与附八字臂 B 相同。这一对不能用来说明「换了别人的八字」。另外两对不是自配对。整张表不是全排列分布，`adjusted_because_draw_was_identity` 为 false：算法只在整表抽成恒等排列时才整体旋转，不保证每个人都避开自己的八字。

以后如果要做无自配对的排列，应使用新的版本名和新的输出目录，并在调用前固定。不要回改本目录的 `result.json`，也不要把它说成已经是无自配对对照。
