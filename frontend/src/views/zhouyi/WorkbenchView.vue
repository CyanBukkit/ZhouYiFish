<template>
  <section v-if="bundle">
    <p class="zy-pill">{{ persona.fictional ? '虚构样例' : '用户档案' }} · 出生地不参与真太阳时</p>
    <h1>{{ persona.display_name }}</h1>
    <form class="zy-form" @submit.prevent="save">
      <div class="zy-split">
        <label>名称 <input v-model="draft.display_name" /></label>
        <label>时区 <input v-model="draft.timezone" /></label>
        <label>出生日期 <input v-model="draft.birth_date" type="date" /></label>
        <label>出生时刻 <input v-model="draft.birth_time" type="time" /></label>
        <label>出生地 <input v-model="draft.birth_place" /></label>
        <label>已知职业 <input v-model="draft.known_occupation" /></label>
      </div>
      <label>生活背景 <textarea v-model="draft.living_background" rows="3" /></label>
      <div class="zy-actions">
        <button>保存</button>
        <button class="secondary" type="button" @click="cast">重新排盘</button>
        <button class="quiet" type="button" @click="remove">删除档案</button>
        <a class="zy-link quiet" :href="`/api/zhouyi/personas/${persona.id}/export.md`">导出 Markdown</a>
      </div>
    </form>

    <article class="zy-card" style="margin-top: 1rem">
      <h2>四柱</h2>
      <p v-if="chart?.pillars" class="zy-pillars">{{ chart.pillars }}</p>
      <p v-else class="zy-warn">{{ chart?.reason || '尚未排成完整四柱。' }}</p>
      <p v-if="chart?.solar_term">当前节：{{ chart.solar_term.active_jie }}（{{ chart.solar_term.active_jie_at }}）。年柱{{ chart.solar_term.year_uses_previous_lichun ? '早于当年立春，沿用上一立春。' : '不早于当年立春。' }}</p>
      <p>{{ chart?.place_notice }} {{ chart?.zi_chu_notice }}</p>
    </article>

    <div class="zy-split" style="margin-top: 1rem">
      <article class="zy-card">
        <h2>用户已知事实</h2>
        <p>职业：{{ persona.known_occupation || '未填' }}</p>
        <p>生活背景：{{ persona.living_background || '未填' }}</p>
        <p v-for="item in facts" :key="item.id">{{ item.name }}：{{ item.relation }}</p>
      </article>
      <article class="zy-card">
        <h2>规则候选与假设</h2>
        <p class="zy-pill">不是真实职业标签</p>
        <p v-if="!bundle.hypotheses.length">排盘完成后，日干候选会出现在这里。</p>
        <p v-for="item in bundle.hypotheses" :key="item.id">{{ item.text }}</p>
        <form @submit.prevent="addNote">
          <label>追加一条自己的备注 <input v-model="note" /></label>
          <button class="quiet" type="submit">放入假设栏</button>
        </form>
      </article>
    </div>

    <article class="zy-card" style="margin-top: 1rem">
      <h2>关系图</h2>
      <svg class="zy-graph" viewBox="0 0 640 280">
        <line v-for="edge in graph.edges" :key="edge.target" :x1="point(edge.source).x" :y1="point(edge.source).y" :x2="point(edge.target).x" :y2="point(edge.target).y" stroke="#9c2f2f" />
        <g v-for="node in graph.nodes" :key="node.id">
          <circle :cx="point(node.id).x" :cy="point(node.id).y" r="28" :fill="node.kind === 'persona' ? '#1f4d3a' : '#9c2f2f'" />
          <text :x="point(node.id).x" :y="point(node.id).y + 46" text-anchor="middle" font-size="14">{{ node.label }}</text>
        </g>
      </svg>
      <form class="zy-row" @submit.prevent="addRelation">
        <input v-model="relation.name" placeholder="名称" />
        <input v-model="relation.relation" placeholder="关系说明" />
        <select v-model="relation.kind">
          <option value="user_fact">用户已知</option>
          <option value="scene_role">场景角色</option>
        </select>
        <button type="submit">加入图中</button>
      </form>
      <button v-for="item in bundle.relations" :key="item.id" class="quiet" type="button" @click="dropRelation(item.id)">移除 {{ item.name }}</button>
    </article>

    <article class="zy-card" style="margin-top: 1rem">
      <h2>低风险场景分析</h2>
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
      <label>对照模型（可空）
        <select v-model="compareModel">
          <option value="">不对照</option>
          <option v-for="item in models" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button @click="run" :disabled="running">运行圆桌</button>
      <p v-if="runError" class="zy-error">{{ runError }}</p>
      <div v-if="analysis">
        <p>状态：{{ analysis.status }} · 引擎 {{ analysis.engine }} · 请求 {{ analysis.requests_used }} · 准确率不计算</p>
        <p v-if="analysis.error" class="zy-error">{{ analysis.error }}</p>
        <div v-for="step in analysis.result?.steps || []" :key="step.step" class="zy-log">{{ step.role }} / {{ step.model }} / {{ step.text || step.error }}</div>
        <p v-if="analysis.result?.summary">{{ analysis.result.summary.action_suggestions || analysis.result.summary.raw_text }}</p>
      </div>
    </article>
  </section>
  <p v-else-if="error" class="zy-error">{{ error }}</p>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { zhouyi } from '../../zhouyi/api'

const route = useRoute()
const router = useRouter()
const bundle = ref(null)
const error = ref('')
const note = ref('')
const scenarios = ref([])
const models = ref(['mimo-v2.6-pro', 'gpt-6-astra'])
const scenario = ref('')
const model = ref('mimo-v2.6-pro')
const compareModel = ref('')
const running = ref(false)
const runError = ref('')
const analysis = ref(null)
const draft = reactive({})
const relation = reactive({ name: '', relation: '', kind: 'scene_role' })

const persona = computed(() => bundle.value?.persona || {})
const chart = computed(() => bundle.value?.chart)
const graph = computed(() => bundle.value?.graph || { nodes: [], edges: [] })
const facts = computed(() => (bundle.value?.relations || []).filter((item) => item.kind === 'user_fact'))

function point(id) {
  const nodes = graph.value.nodes
  const index = Math.max(0, nodes.findIndex((node) => node.id === id))
  if (index === 0) return { x: 320, y: 120 }
  const angle = ((index - 1) / Math.max(1, nodes.length - 1)) * Math.PI * 2
  return { x: 320 + Math.cos(angle) * 180, y: 130 + Math.sin(angle) * 80 }
}

async function load() {
  bundle.value = await zhouyi(`/api/zhouyi/personas/${route.params.id}`)
  Object.assign(draft, bundle.value.persona)
}

async function save() {
  error.value = ''
  try {
    bundle.value = await zhouyi(`/api/zhouyi/personas/${route.params.id}`, { method: 'PATCH', body: draft })
  } catch (err) {
    error.value = err.message
  }
}

async function cast() {
  bundle.value = await zhouyi(`/api/zhouyi/personas/${route.params.id}/chart`, { method: 'POST', body: {} })
}

async function remove() {
  await zhouyi(`/api/zhouyi/personas/${route.params.id}`, { method: 'DELETE' })
  router.push('/personas')
}

async function addNote() {
  if (!note.value.trim()) return
  bundle.value = await zhouyi(`/api/zhouyi/personas/${route.params.id}/hypotheses`, { method: 'POST', body: { text: note.value } })
  note.value = ''
}

async function addRelation() {
  bundle.value = await zhouyi(`/api/zhouyi/personas/${route.params.id}/relations`, { method: 'POST', body: relation })
  relation.name = ''
  relation.relation = ''
}

async function dropRelation(id) {
  await zhouyi(`/api/zhouyi/relations/${id}`, { method: 'DELETE' })
  await load()
}

async function run() {
  running.value = true
  runError.value = ''
  try {
    analysis.value = await zhouyi('/api/zhouyi/analyses', {
      method: 'POST',
      body: { persona_id: route.params.id, scenario: scenario.value, model: model.value, compare_model: compareModel.value || null, budget: 8 },
    })
    if (analysis.value.status === 'queued' || analysis.value.status === 'running') {
      for (let i = 0; i < 20; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, 500))
        analysis.value = await zhouyi(`/api/zhouyi/analyses/${analysis.value.id}`)
        if (!['queued', 'running'].includes(analysis.value.status)) break
      }
    }
  } catch (err) {
    runError.value = err.message
  } finally {
    running.value = false
  }
}

onMounted(async () => {
  try {
    const meta = await zhouyi('/api/zhouyi/meta')
    scenarios.value = meta.scenarios
    scenario.value = meta.scenarios[0]
    const settings = await zhouyi('/api/zhouyi/settings')
    models.value = settings.available_models
    model.value = settings.model
    await load()
  } catch (err) {
    error.value = err.message
  }
})
</script>
