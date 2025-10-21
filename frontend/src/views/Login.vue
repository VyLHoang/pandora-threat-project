<template>
  <div class="auth-container">
    <div class="auth-card">
      <h1>🛡️ Pandora Security</h1>
      <h2>Login</h2>
      
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>Email</label>
          <input 
            v-model="email" 
            type="email" 
            placeholder="your@email.com"
            required
          />
        </div>
        
        <div class="form-group">
          <label>Password</label>
          <input 
            v-model="password" 
            type="password" 
            placeholder="••••••••"
            required
          />
        </div>
        
        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
      </form>
      
      <p class="auth-link">
        Don't have an account? 
        <router-link to="/register">Register here</router-link>
      </p>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authAPI } from '../services/api'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const email = ref('')
    const password = ref('')
    const loading = ref(false)
    const error = ref('')

    const handleLogin = async () => {
      loading.value = true
      error.value = ''
      
      try {
        console.log('[login] attempting login with', email.value)
        const loginResp = await authAPI.login(email.value, password.value)
        console.log('[login] login response:', loginResp.data)

        // Đợi 300ms để cookies được set bởi browser
        await new Promise(resolve => setTimeout(resolve, 300))

        // Verify cookies bằng cách gọi /auth/me
        console.log('[login] verifying cookies with /auth/me...')
        const meResp = await authAPI.getMe()
        console.log('[login] user verified:', meResp.data)

        const user = meResp.data
        localStorage.setItem('user', JSON.stringify(user))
        console.log('[login] user data stored in localStorage')

        // Navigate to dashboard
        console.log('[login] navigating to /dashboard...')
        await router.push('/dashboard')
        console.log('[login] navigation success -> /dashboard')
        
      } catch (err) {
        console.error('[login] error', err)
        if (err.response?.status === 401) {
          error.value = '❌ Incorrect email or password'
        } else if (err.response?.status === 403) {
          error.value = '❌ Account is inactive'
        } else {
          error.value = err.response?.data?.detail || '❌ Login failed. Please try again.'
        }
      } finally {
        loading.value = false
      }
    }

    return {
      email,
      password,
      loading,
      error,
      handleLogin
    }
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  padding: 20px;
}

.auth-card {
  background: #1a1a1a;
  border: 3px solid #FFD700;
  padding: 40px;
  max-width: 400px;
  width: 100%;
}

h1 {
  color: #FFD700;
  text-align: center;
  margin-bottom: 10px;
  font-size: 2em;
}

h2 {
  color: #FFD700;
  text-align: center;
  margin-bottom: 30px;
  font-size: 1.5em;
}

.error-message {
  background: #ff000020;
  border: 2px solid #ff0000;
  color: #ff6666;
  padding: 10px;
  margin-bottom: 20px;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  color: #FFD700;
  margin-bottom: 8px;
  font-weight: bold;
}

input {
  width: 100%;
  padding: 12px;
  background: #000;
  border: 2px solid #FFD700;
  color: #FFF;
  font-size: 16px;
  font-family: 'Courier New', monospace;
}

input:focus {
  outline: none;
  border-color: #FFA500;
}

.btn-primary {
  width: 100%;
  padding: 15px;
  background: #FFD700;
  color: #000;
  border: none;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  font-family: 'Courier New', monospace;
  transition: all 0.3s;
}

.btn-primary:hover:not(:disabled) {
  background: #FFA500;
  transform: translateY(-2px);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.auth-link {
  text-align: center;
  margin-top: 20px;
  color: #FFF;
}

.auth-link a {
  color: #FFD700;
  text-decoration: none;
}

.auth-link a:hover {
  text-decoration: underline;
}
</style>

