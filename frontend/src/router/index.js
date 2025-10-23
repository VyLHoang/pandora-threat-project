import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Dashboard from '../views/Dashboard.vue'
import Scanner from '../views/Scanner.vue'
import History from '../views/History.vue'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresGuest: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/scanner',
    name: 'Scanner',
    component: Scanner,
    meta: { requiresAuth: true }
  },
  {
    path: '/history',
    name: 'History',
    component: History,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory('/app/'),  // Real app hidden at /app/ path
  routes
})

// Navigation guards
import { authAPI } from '../services/api'

router.beforeEach(async (to, from, next) => {
  // Use 'user' in localStorage as login state
  const user = localStorage.getItem('user')
  console.log('[router.beforeEach] to:', to.fullPath, 'user exists?', !!user)

  if (to.meta.requiresAuth && !user) {
    // Try to fetch user from backend using cookie (in case of reload)
    try {
      const res = await authAPI.getMe()
      localStorage.setItem('user', JSON.stringify(res.data))
      return next()
    } catch (e) {
      console.log('[router.beforeEach] getMe failed', e)
      return next('/login')
    }
  } else if (to.meta.requiresGuest && user) {
    return next('/dashboard')
  } else {
    return next()
  }
})

export default router

