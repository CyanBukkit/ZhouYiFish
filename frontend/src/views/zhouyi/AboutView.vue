<template>
  <section>
    <h1>说明与边界</h1>
    <article class="zy-card">
      <h2>已经接上的</h2>
      <ul>
        <li>中文工作台：档案、四柱、事实/假设分栏、关系图、圆桌、实验、模型设置、历史和导出。</li>
        <li>四柱使用 research.bazi 与 sxtwl 的节气时刻。年界是立春时刻，月界是节而不是中气。</li>
        <li>五步规则链版本 yhzp-month-command-v1：旺衰、月令取格、扶抑喜忌、十神配合、大运流年。没有密钥也能计算、保存和导出。</li>
        <li>数据在本机 SQLite。没有密钥时服务可以启动。</li>
        <li>圆桌引擎名称是 zhouyi_roundtable_v1。</li>
      </ul>
    </article>
    <article class="zy-card" style="margin-top: 1rem">
      <h2>没有做成或没有通过的</h2>
      <ul>
        <li>真实模型端到端：这台云主机没有可用密钥，页面上的分析会失败而不是显示伪造回答。</li>
        <li>原版 OASIS 群体仿真和 Zep 图谱记忆。缺 Zep 不阻止本产品。</li>
        <li>真太阳时和子初换日。</li>
        <li>对真实行为的准确率。没有结局标签。</li>
        <li>2026-11-17 用户电脑上的四次 HTTP 500 是另一环境的探针，不是本页面调用，也不能证明接口本身损坏。</li>
      </ul>
    </article>
    <article class="zy-card" style="margin-top: 1rem">
      <h2>上游</h2>
      <p>群体仿真界面来自 <a href="https://github.com/666ghj/MiroFish">MiroFish</a>，许可证 AGPL-3.0。入口保留在「上游界面」。本仓库的研究记录在 <a href="https://github.com/CyanBukkit/ZhouYiFish">ZhouYiFish</a>。</p>
    </article>
  </section>
</template>
