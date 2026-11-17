import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Shell from '../views/zhouyi/Shell.vue'
import ZhouyiHome from '../views/zhouyi/HomeView.vue'
import Personas from '../views/zhouyi/PersonasView.vue'
import Workbench from '../views/zhouyi/WorkbenchView.vue'
import Experiment from '../views/zhouyi/ExperimentView.vue'
import Settings from '../views/zhouyi/SettingsView.vue'
import History from '../views/zhouyi/HistoryView.vue'
import About from '../views/zhouyi/AboutView.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'

const routes = [
  {
    path: '/',
    component: Shell,
    children: [
      { path: '', name: 'ZhouyiHome', component: ZhouyiHome },
      { path: 'personas', name: 'Personas', component: Personas },
      { path: 'workbench/:id', name: 'Workbench', component: Workbench },
      { path: 'experiment', name: 'Experiment', component: Experiment },
      { path: 'settings', name: 'Settings', component: Settings },
      { path: 'history', name: 'History', component: History },
      { path: 'about', name: 'About', component: About }
    ]
  },
  {
    path: '/mirofish',
    name: 'MiroFishHome',
    component: Home
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
