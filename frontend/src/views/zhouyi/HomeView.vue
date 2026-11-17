<template>
  <section>
    <p class="zy-pill">实验性产品 · 不声称预测更准</p>
    <h1>从生辰到可核对的人物工作台</h1>
    <p class="zy-lead">建立档案，用已核对的节气规则排四柱，把你写下的事实和规则假设分开，再画关系、跑低风险场景。没有模型密钥时，排盘和档案仍然可用，分析会明确失败，不会编造结果。</p>
    <div class="zy-actions">
      <button @click="loadExample" :disabled="busy">加载沙盒甲</button>
      <button class="secondary" @click="loadNamed('/api/zhouyi/examples/sandbox-qiang')" :disabled="busy">加载沙盒强</button>
      <button class="quiet" @click="loadNamed('/api/zhouyi/examples/sandbox-ruo')" :disabled="busy">加载沙盒弱</button>
      <router-link class="zy-link secondary" to="/personas">新建自己的档案</router-link>
      <router-link class="zy-link quiet" to="/settings">模型设置</router-link>
    </div>
    <p v-if="error" class="zy-error">{{ error }}</p>
    <div class="zy-grid" style="margin-top: 1.2rem">
      <article class="zy-card">
        <h2>这次能做完的流程</h2>
        <ol>
          <li>填写出生日期、时刻、时区和出生地。</li>
          <li>排出四柱，并写明节气、换日和未知时刻的限制。</li>
          <li>编辑已知职业、生活背景和关系。日干候选留在假设栏。</li>
          <li>关系图来自刚保存的后端数据。</li>
          <li>选择合作或沟通场景，运行圆桌或看到未配置错误。</li>
        </ol>
      </article>
      <article class="zy-card">
        <h2>这次不声称的事</h2>
        <ul>
          <li>八字不决定职业，假设不是真实标签。</li>
          <li>圆桌引擎叫 zhouyi_roundtable_v1，不是原版 OASIS。</li>
          <li>没有真实结局时不计算准确率。</li>
          <li>Zep 是可选增强，缺了也不会挡住排盘。</li>
        </ul>
      </article>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { zhouyi } from '../../zhouyi/api'

const router = useRouter()
const busy = ref(false)
const error = ref('')

async function loadNamed(path) {
  busy.value = true
  error.value = ''
  try {
    const bundle = await zhouyi(path, { method: 'POST', body: {} })
    router.push(`/workbench/${bundle.persona.id}`)
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

function loadExample() {
  return loadNamed('/api/zhouyi/examples/sandbox-jia')
}
</script>
