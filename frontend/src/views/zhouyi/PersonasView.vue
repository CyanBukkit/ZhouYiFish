<template>
  <section>
    <h1>人物档案</h1>
    <div class="zy-split">
      <form class="zy-form" @submit.prevent="create">
        <h2>新建</h2>
        <label>名称 <input v-model="form.display_name" required /></label>
        <label>出生日期 <input v-model="form.birth_date" type="date" /></label>
        <label>出生时刻 <input v-model="form.birth_time" type="time" /></label>
        <label>时区 <input v-model="form.timezone" /></label>
        <label>出生地 <input v-model="form.birth_place" placeholder="只存档，不参与真太阳时" /></label>
        <label>已知职业 <input v-model="form.known_occupation" placeholder="只写你已经知道的，不要填八字推出的职业" /></label>
        <label>生活背景 <textarea v-model="form.living_background" rows="3" /></label>
        <label>排运
          <select v-model="form.luck_mode">
            <option value="">待补齐</option>
            <option value="manual">手选顺逆</option>
            <option value="traditional">传统性别规则</option>
          </select>
        </label>
        <label>顺逆
          <select v-model="form.luck_direction">
            <option value="">未选</option>
            <option value="forward">顺</option>
            <option value="backward">逆</option>
          </select>
        </label>
        <label>传统规则所用性别
          <select v-model="form.luck_sex">
            <option value="">不选</option>
            <option value="male">男</option>
            <option value="female">女</option>
          </select>
        </label>
        <label><input type="checkbox" v-model="form.fictional" /> 这是虚构档案</label>
        <button :disabled="busy">保存并排盘</button>
        <p v-if="error" class="zy-error">{{ error }}</p>
      </form>
      <div class="zy-list">
        <h2>已保存</h2>
        <p v-if="!people.length">还没有档案。</p>
        <article v-for="person in people" :key="person.id" style="margin-bottom: 0.8rem">
          <strong>{{ person.display_name }}</strong>
          <span class="zy-pill">{{ person.fictional ? '虚构' : '用户档案' }}</span>
          <p>{{ person.birth_date || '未填日期' }} {{ person.birth_time || '时刻未知' }} · {{ person.pillars || '未排成四柱' }}</p>
          <router-link :to="`/workbench/${person.id}`">打开工作台</router-link>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { zhouyi } from '../../zhouyi/api'

const router = useRouter()
const people = ref([])
const busy = ref(false)
const error = ref('')
const form = reactive({
  display_name: '',
  birth_date: '',
  birth_time: '',
  timezone: 'Asia/Shanghai',
  birth_place: '',
  known_occupation: '',
  living_background: '',
  fictional: true,
  luck_mode: '',
  luck_direction: '',
  luck_sex: '',
})

async function refresh() {
  people.value = await zhouyi('/api/zhouyi/personas')
}

async function create() {
  busy.value = true
  error.value = ''
  try {
    const created = await zhouyi('/api/zhouyi/personas', { method: 'POST', body: form })
    await zhouyi(`/api/zhouyi/personas/${created.id}/chart`, { method: 'POST', body: {} })
    router.push(`/workbench/${created.id}`)
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

onMounted(refresh)
</script>
