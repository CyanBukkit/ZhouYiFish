<template>
  <div class="zy">
    <nav class="zy-nav">
      <router-link class="zy-brand" to="/">周易鱼</router-link>
      <router-link to="/personas">人物</router-link>
      <router-link to="/experiment">实验</router-link>
      <router-link to="/settings">模型</router-link>
      <router-link to="/history">历史</router-link>
      <router-link to="/about">说明</router-link>
      <router-link to="/mirofish">上游界面</router-link>
    </nav>
    <main class="zy-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import '../../zhouyi/zhouyi.css'
</script>
