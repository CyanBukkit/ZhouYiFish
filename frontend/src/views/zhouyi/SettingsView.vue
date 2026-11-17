<template>
  <section>
    <h1>模型设置</h1>
    <p v-if="view" class="zy-warn" v-show="view.plaintext_http">{{ view.plaintext_warning }}</p>
    <article class="zy-card">
      <p>密钥：{{ view?.key_mask || '读取中' }}</p>
      <p>来源：{{ view?.key_source }}</p>
      <p>端点：{{ view?.base_url }}</p>
      <p>当前模型：{{ view?.model }}</p>
      <p>研究命令行看不到这次页面提交的内存密钥。</p>
      <ol>
        <li v-for="item in view?.priority || []" :key="item">{{ item }}</li>
      </ol>
    </article>
    <form class="zy-form" @submit.prevent="save">
      <label>端点 <input v-model="baseUrl" autocomplete="off" /></label>
      <label>默认模型
        <select v-model="model">
          <option v-for="item in view?.available_models || []" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label>密钥（只提交到服务器内存，页面不回显）
        <input v-model="apiKey" type="password" autocomplete="new-password" />
      </label>
      <div class="zy-actions">
        <button>保存</button>
        <button class="quiet" type="button" @click="clearKey">清除内存密钥</button>
        <button class="secondary" type="button" @click="testConnection">连接测试</button>
      </div>
    </form>
    <p v-if="message" class="zy-ok">{{ message }}</p>
    <p v-if="error" class="zy-error">{{ error }}</p>
    <p>历史探针里的 HTTP 500 来自另一台电脑，不能据此断定这个端点对其它客户端不可用。这里的测试只代表这一次、这一进程。</p>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { zhouyi } from '../../zhouyi/api'

const view = ref(null)
const baseUrl = ref('')
const model = ref('mimo-v2.6-pro')
const apiKey = ref('')
const message = ref('')
const error = ref('')

async function refresh() {
  view.value = await zhouyi('/api/zhouyi/settings')
  baseUrl.value = view.value.base_url
  model.value = view.value.model
}

async function save() {
  message.value = ''
  error.value = ''
  const body = { base_url: baseUrl.value, model: model.value }
  if (apiKey.value) body.api_key = apiKey.value
  try {
    view.value = await zhouyi('/api/zhouyi/settings', { method: 'POST', body })
    apiKey.value = ''
    message.value = '已保存。页面只保留掩码。'
  } catch (err) {
    error.value = err.message
  }
}

async function clearKey() {
  view.value = await zhouyi('/api/zhouyi/settings', { method: 'POST', body: { clear_key: true } })
  message.value = '已清除本进程内存中的密钥。环境变量若仍存在，会继续生效。'
}

async function testConnection() {
  message.value = ''
  error.value = ''
  try {
    const result = await zhouyi('/api/zhouyi/settings/test', { method: 'POST', body: { model: model.value } })
    message.value = `连接返回 ${result.http_status}，延迟 ${result.latency_ms} ms。`
  } catch (err) {
    error.value = err.message
  }
}

onMounted(refresh)
</script>
