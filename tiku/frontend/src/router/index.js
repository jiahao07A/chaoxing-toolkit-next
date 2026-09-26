import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/questions',
    children: [
      {
        path: 'questions',
        name: 'Questions',
        component: () => import('../views/Questions.vue')
      },
      {
        path: 'pending',
        name: 'Pending',
        component: () => import('../views/Pending.vue')
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/Settings.vue')
      },
      {
        path: 'match-quality',
        name: 'MatchQuality',
        component: () => import('../views/MatchQuality.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
