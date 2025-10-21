<template>
  <div class="auth-container">
    <div class="auth-card">
      <h1>🛡️ Pandora Security</h1>
      <h2>Create Account</h2>
      
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      
      <div v-if="success" class="success-message">
        {{ success }}
      </div>
      
      <div class="requirements-box">
        <h3>📋 Account Requirements:</h3>
        <ul>
          <li :class="{ valid: username.length >= 3 }">
            Username: at least 3 characters
          </li>
          <li :class="{ valid: emailValid }">
            Email: valid email format
          </li>
          <li :class="{ valid: password.length >= 8 }">
            Password: at least 8 characters
          </li>
          <li :class="{ valid: hasUpperCase }">
            Password: contains uppercase letter
          </li>
          <li :class="{ valid: hasLowerCase }">
            Password: contains lowercase letter
          </li>
          <li :class="{ valid: hasNumber }">
            Password: contains number
          </li>
        </ul>
      </div>

      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label>Username</label>
          <input 
            v-model="username" 
            type="text" 
            placeholder="username"
            required
            minlength="3"
          />
          <small class="hint">Minimum 3 characters</small>
        </div>
        
        <div class="form-group">
          <label>Email</label>
          <input 
            v-model="email" 
            type="email" 
            placeholder="your@email.com"
            required
          />
          <small class="hint">Must be a valid email address</small>
        </div>
        
        <div class="form-group">
          <label>Password</label>
          <input 
            v-model="password" 
            type="password" 
            placeholder="••••••••"
            required
            minlength="8"
          />
          <small class="hint">Min 8 chars with uppercase, lowercase & number</small>
        </div>
        
        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? 'Creating account...' : 'Register' }}
        </button>
      </form>
      
      <p class="auth-link">
        Already have an account? 
        <router-link to="/login">Login here</router-link>
      </p>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { authAPI } from '../services/api'

export default {
  name: 'Register',
  setup() {
    const router = useRouter()
    const username = ref('')
    const email = ref('')
    const password = ref('')
    const loading = ref(false)
    const error = ref('')
    const success = ref('')

    // Computed validation
    const emailValid = computed(() => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      return email.value.length === 0 || emailRegex.test(email.value)
    })

    const hasUpperCase = computed(() => /[A-Z]/.test(password.value))
    const hasLowerCase = computed(() => /[a-z]/.test(password.value))
    const hasNumber = computed(() => /[0-9]/.test(password.value))

    const isFormValid = computed(() => {
      return username.value.length >= 3 &&
             emailValid.value &&
             password.value.length >= 8 &&
             hasUpperCase.value &&
             hasLowerCase.value &&
             hasNumber.value
    })

    const handleRegister = async () => {
      // Client-side validation
      if (!isFormValid.value) {
        error.value = 'Please meet all requirements above'
        return
      }

      loading.value = true
      error.value = ''
      success.value = ''
      
      try {
        const response = await authAPI.register(
          email.value,
          username.value,
          password.value
        )
        
        console.log('[register] response:', response.data)
        
        // Token đã được set vào HTTPOnly cookie bởi backend - AN TOÀN!
        // Cookies được browser tự động lưu, không cần localStorage
        
        // Hiển thị success message
        success.value = '✅ Account created successfully! Logging in...'
        error.value = '' // Clear error
        
        // Đợi 500ms để cookies được set, sau đó gọi /auth/me để verify
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // Verify cookies bằng cách gọi /auth/me
        console.log('[register] verifying cookies with /auth/me...')
        const meResp = await authAPI.getMe()
        console.log('[register] user verified:', meResp.data)
        
        // Lưu user info để hiển thị UI
        const user = meResp.data
        localStorage.setItem('user', JSON.stringify(user))
        console.log('[register] user data stored in localStorage')
        
        // Navigate to dashboard
        success.value = '✅ Redirecting to dashboard...'
        setTimeout(async () => {
          try {
            await router.push('/dashboard')
            console.log('[register] navigation success -> /dashboard')
          } catch (navErr) {
            console.error('[register] router.push failed:', navErr)
          }
        }, 500)
        
      } catch (err) {
        console.error('Register error:', err) // Debug
        
        // Clear success message
        success.value = ''
        
        // Enhanced error messages
        if (err.response) {
          const detail = err.response.data?.detail
          const status = err.response.status
          
          if (status === 400) {
            if (detail && typeof detail === 'string') {
              if (detail.includes('already registered') || detail.includes('Email already')) {
                error.value = '❌ This email is already registered!'
              } else if (detail.includes('already taken') || detail.includes('Username already')) {
                error.value = '❌ This username is already taken!'
              } else {
                error.value = `❌ ${detail}`
              }
            } else if (Array.isArray(detail)) {
              // Pydantic validation errors
              error.value = `❌ Validation error: ${detail[0].msg}`
            } else {
              error.value = '❌ Invalid registration data!'
            }
          } else if (status === 500) {
            error.value = '❌ Server error. Please try again later.'
          } else {
            error.value = detail || 'Registration failed. Please try again.'
          }
        } else if (err.request) {
          error.value = '❌ Cannot connect to server. Please check your connection.'
        } else {
          error.value = '❌ Registration failed. Please try again.'
        }
      } finally {
        loading.value = false
      }
    }

    return {
      username,
      email,
      password,
      loading,
      error,
      success,
      emailValid,
      hasUpperCase,
      hasLowerCase,
      hasNumber,
      isFormValid,
      handleRegister
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

.success-message {
  background: #00ff0020;
  border: 2px solid #00ff00;
  color: #66ff66;
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

