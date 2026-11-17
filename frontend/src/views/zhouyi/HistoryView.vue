<template>
  <section>
    <h1>运行历史</h1>
    <div class="zy-actions">
      <button class="quiet" @click="refresh">刷新</button>
    </div>
    <h2>圆桌</h2>
    <table class="zy-table">
      <tr><th>时间</th><th>人物</th><th>场景</th><th>状态</th><th>请求</th></tr>
      <tr v-for="item in analyses" :key="item.id">
        <td>{{ item.created_at }}</td>
        <td>{{ item.persona_name }}</td>
        <td>{{ item.scenario }}</td>
        <td>{{ item.status }} {{ item.error || '' }}</td>
        <td>{{ item.requests_used }} <button v-if="item.status === 'running'" class="quiet" @click="cancel(item.id)">取消</button></td>
      </tr>
    </table>
    <h2>实验</h2>
    <table class="zy-table">
      <tr><th>时间</th><th>人物</th><th>状态</th><th>请求</th><th>准确率</th></tr>
      <tr v-for="item in experiments" :key="item.id">
        <td>{{ item.created_at }}</td>
        <td>{{ item.persona_name }}</td>
        <td>{{ item.status }} {{ item.error || '' }}</td>
        <td>{{ item.requests_used }}</td>
        <td>不计算</td>
      </tr>
    </table>
    <p v-if="error" class="zy-error">{{ error }}</p>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { zhouyi } from '../../zhouyi/api'

const analyses = ref([])
const experiments = ref([])
const error = ref('')

async function refresh() {
  try {
    analyses.value = await zhouyi('/api/zhouyi/analyses')
    experiments.value = await zhouyi('/api/zhouyi/experiments')
  } catch (err) {
    error.value = err.message
  }
}

async function cancel(id) {
  await zhouyi(`/api/zhouyi/analyses/${id}/cancel`, { method: 'POST', body: {} })
  await refresh()
}

onMounted(refresh)
</script>
