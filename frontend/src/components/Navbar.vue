<template>
  <nav class="navbar">
    <div class="nav-brand">
      <h1>🛡️ Pandora Security</h1>
    </div>
    
    <div class="nav-links">
      <router-link to="/dashboard">Dashboard</router-link>
      <router-link to="/scanner">Scanner</router-link>
      <router-link to="/history">History</router-link>
      <button @click="handleLogout" class="btn-logout">Logout</button>
    </div>
  </nav>
</template>

<script>
import { useRouter } from 'vue-router'
import { authAPI } from '../services/api'

export default {
  name: 'Navbar',
  setup() {
    const router = useRouter()

    const handleLogout = async () => {
      await authAPI.logout()
      router.push('/login')
    }

    return { handleLogout }
  }
}
</script>

<style scoped>
.navbar {
  background: #1a1a1a;
  border-bottom: 3px solid #FFD700;
  padding: 15px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-brand h1 {
  color: #FFD700;
  font-size: 1.5em;
  margin: 0;
}

.nav-links {
  display: flex;
  gap: 20px;
  align-items: center;
}

.nav-links a {
  color: #FFD700;
  text-decoration: none;
  font-weight: bold;
  padding: 10px 15px;
  transition: all 0.3s;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  background: #FFD700;
  color: #000;
}

.btn-logout {
  background: #ff0000;
  color: #FFF;
  border: none;
  padding: 10px 20px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-logout:hover {
  background: #cc0000;
}
</style>

