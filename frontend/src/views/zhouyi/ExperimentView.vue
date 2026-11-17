<template>
  <section>
    <h1>四臂对照</h1>
    <p>同一人物事实和场景，比较无八字、真实八字、无自配对打乱八字、等长中性信息。原始 v1 打乱表不回改。没有真实结局时只看输出差异、完成数、延迟和 usage。</p>
    <form class="zy-form" @submit.prevent="run">
      <label>人物
        <select v-model="personaId" required>
          <option v-for="person in people" :key="person.id" :value="person.id">{{ person.display_name }} · {{ person.pillars || '未排盘' }}</option>
        </select>
      </label>
      <label>场景
        <select v-model="scenario">
          <option v-for="item in scenarios" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label>模型
        <select v-model="model">
          <option v-for="item in models" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label>预算 <input v-model.number="budget" type="number" min="1" max="60" /></label>
      <button :disabled="busy">准备并运行</button>
    </form>
    <p v-if="error" class="zy-error">{{ error }}</p>
    <article v-if="experiment" class="zy-card" style="margin-top: 1rem">
      <p>状态：{{ experiment.status }} · 请求 {{ experiment.requests_used }} · 准确率：不计算</p>
      <p v-if="experiment.error">{{ experiment.error }}</p>
      <p v-if="experiment.result">完成 {{ experiment.result.completion_count || 0 }} / {{ experiment.result.arm_count || 4 }} · 文本是否不同：{{ experiment.result.texts_differ ? '是' : '尚无成功输出可比较' }}</p>
      <table class="zy-table" v-if="experiment.result?.arms">
        <tr><th>臂</th><th>提示或阻塞</th><th>输出</th></tr>
        <tr v-for="(arm, name) in experiment.result.arms" :key="name">
          <td>{{ name }}</td>
          <td>{{ arm.error || arm.prompt }}</td>
          <td>{{ arm.output?.text || arm.output?.error || '未调用' }}</td>
        </tr>
      </table>
    </article>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { zhouyi } from '../../zhouyi/api'

const people = ref([])
const scenarios = ref([])
const models = ref(['mimo-v2.6-pro', 'gpt-6-astra'])
const personaId = ref('')
const scenario = ref('')
const model = ref('mimo-v2.6-pro')
const budget = ref(8)
const busy = ref(false)
const error = ref('')
const experiment = ref(null)

async function run() {
  busy.value = true
  error.value = ''
  try {
    experiment.value = await zhouyi('/api/zhouyi/experiments', {
      method: 'POST',
      body: { persona_id: personaId.value, scenario: scenario.value, model: model.value, budget: budget.value },
    })
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  people.value = await zhouyi('/api/zhouyi/personas')
  personaId.value = people.value[0]?.id || ''
  const meta = await zhouyi('/api/zhouyi/meta')
  scenarios.value = meta.scenarios
  scenario.value = meta.scenarios[0]
  const settings = await zhouyi('/api/zhouyi/settings')
  models.value = settings.available_models
  model.value = settings.model
})
</script>
