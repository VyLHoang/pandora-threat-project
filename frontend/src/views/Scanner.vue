<template>
  <div class="scanner-container">
    <div class="scanner-header">
      <h1>🔍 Threat Scanner</h1>
      <p>Scan IP addresses and file hashes with VirusTotal</p>
    </div>

    <!-- Scan Type Tabs -->
    <div class="tabs">
      <button 
        :class="['tab', { active: scanType === 'ip' }]"
        @click="scanType = 'ip'"
      >
        IP Address
      </button>
      <button 
        :class="['tab', { active: scanType === 'hash' }]"
        @click="scanType = 'hash'"
      >
        File Hash
      </button>
    </div>

    <!-- Scanner Form -->
    <div class="scanner-form">
      <div v-if="scanType === 'ip'" class="form-group">
        <label>Enter IP Address</label>
        <input 
          v-model="ipAddress" 
          type="text" 
          placeholder="8.8.8.8"
          @keyup.enter="handleScan"
        />
        <p class="hint">Example: 8.8.8.8, 1.1.1.1</p>
      </div>

      <div v-else class="form-group">
        <label>Enter File Hash (MD5/SHA1/SHA256)</label>
        <input 
          v-model="fileHash" 
          type="text" 
          placeholder="44d88612fea8a8f36de82e1278abb02f"
          @keyup.enter="handleScan"
        />
        <p class="hint">Example: 44d88612fea8a8f36de82e1278abb02f</p>
      </div>

      <button 
        @click="handleScan" 
        class="btn-scan"
        :disabled="loading"
      >
        {{ loading ? 'Scanning...' : '🔎 Scan Now' }}
      </button>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>

    <!-- Scan Result -->
    <div v-if="result" class="result-container">
      <div class="result-header">
        <h2>Scan Result</h2>
        <span :class="['badge', result.is_malicious ? 'badge-danger' : 'badge-safe']">
          {{ result.is_malicious ? '⚠️ MALICIOUS' : '✅ SAFE' }}
        </span>
      </div>

      <div class="result-body">
        <div class="result-item">
          <strong>Target:</strong> {{ result.target }}
        </div>
        <div class="result-item">
          <strong>Detection:</strong> 
          {{ result.detection_count || 0 }} / {{ result.total_engines || 0 }} engines
        </div>
        
        <div v-if="result.threat_names && result.threat_names.length > 0" class="result-item">
          <strong>Threats Found:</strong>
          <ul class="threat-list">
            <li v-for="(threat, idx) in result.threat_names" :key="idx">
              {{ threat }}
            </li>
          </ul>
        </div>

        <div v-if="result.country" class="result-item">
          <strong>Country:</strong> {{ result.country }}
        </div>

        <div v-if="result.as_owner" class="result-item">
          <strong>AS Owner:</strong> {{ result.as_owner }}
        </div>

        <!-- WHOIS Information (for IP scans) -->
        <div v-if="result.whois_data && result.whois_data.success && scanType === 'ip'" class="whois-section">
          <h3>🌐 WHOIS Information</h3>
          <div class="whois-grid">
            <div v-if="result.whois_data.domain_name" class="whois-item">
              <strong>Domain:</strong> {{ result.whois_data.domain_name }}
            </div>
            <div v-if="result.whois_data.registrar" class="whois-item">
              <strong>Registrar:</strong> {{ result.whois_data.registrar }}
            </div>
            <div v-if="result.whois_data.organization" class="whois-item">
              <strong>Organization:</strong> {{ result.whois_data.organization }}
            </div>
            <div v-if="result.whois_data.country" class="whois-item">
              <strong>Country:</strong> {{ result.whois_data.country }}
            </div>
            <div v-if="result.whois_data.city" class="whois-item">
              <strong>City:</strong> {{ result.whois_data.city }}
            </div>
            <div v-if="result.whois_data.state" class="whois-item">
              <strong>State:</strong> {{ result.whois_data.state }}
            </div>
            <div v-if="result.whois_data.creation_date" class="whois-item">
              <strong>Created:</strong> {{ formatDate(result.whois_data.creation_date) }}
            </div>
            <div v-if="result.whois_data.expiration_date" class="whois-item">
              <strong>Expires:</strong> {{ formatDate(result.whois_data.expiration_date) }}
            </div>
            <div v-if="result.whois_data.name_servers && result.whois_data.name_servers.length > 0" class="whois-item">
              <strong>Name Servers:</strong>
              <ul class="whois-list">
                <li v-for="(ns, idx) in result.whois_data.name_servers.slice(0, 3)" :key="idx">
                  {{ ns }}
                </li>
              </ul>
            </div>
            <div v-if="result.whois_data.emails && result.whois_data.emails.length > 0" class="whois-item">
              <strong>Contact Emails:</strong>
              <ul class="whois-list">
                <li v-for="(email, idx) in result.whois_data.emails.slice(0, 2)" :key="idx">
                  {{ email }}
                </li>
              </ul>
            </div>
          </div>
          <div v-if="result.whois_data.note" class="whois-note">
            <small>{{ result.whois_data.note }}</small>
          </div>
        </div>

        <div v-if="result.file_type" class="result-item">
          <strong>File Type:</strong> {{ result.file_type }}
        </div>

        <div v-if="result.stats" class="stats-grid">
          <div class="stat-box">
            <div class="stat-value">{{ result.stats.malicious || 0 }}</div>
            <div class="stat-label">Malicious</div>
          </div>
          <div class="stat-box">
            <div class="stat-value">{{ result.stats.suspicious || 0 }}</div>
            <div class="stat-label">Suspicious</div>
          </div>
          <div class="stat-box">
            <div class="stat-value">{{ result.stats.harmless || 0 }}</div>
            <div class="stat-label">Harmless</div>
          </div>
          <div class="stat-box">
            <div class="stat-value">{{ result.stats.undetected || 0 }}</div>
            <div class="stat-label">Undetected</div>
          </div>
        </div>
      </div>

      <!-- Engine Detection Details -->
      <div v-if="result.engine_results && result.engine_results.length > 0" class="engine-results">
        <h3>🔍 Detection Details by Engine</h3>
        <p class="engine-count">{{ result.engine_results.length }} antivirus engines analyzed</p>
        <div class="engine-list">
          <div 
            v-for="(engine, idx) in result.engine_results" 
            :key="idx"
            :class="['engine-item', `category-${engine.category}`]"
          >
            <span class="engine-name">{{ engine.engine }}</span>
            <span class="engine-result">{{ engine.result || 'clean' }}</span>
            <span :class="['engine-category', engine.category]">
              {{ engine.category.toUpperCase() }}
            </span>
          </div>
        </div>
      </div>

      <!-- Auto-Polling Controls -->
      <div class="polling-controls">
        <div class="polling-header">
          <label class="polling-toggle">
            <input 
              type="checkbox" 
              v-model="pollingEnabled" 
              @change="togglePolling"
            />
            <span class="toggle-label">⏱️ Auto-Rescan</span>
          </label>
          <span v-if="pollingEnabled" class="countdown">
            Next scan in: <strong>{{ countdown }}s</strong>
          </span>
        </div>
        <p class="polling-info">
          {{ pollingEnabled ? 'Target will be rescanned every 60 seconds' : 'Enable to continuously monitor this target' }}
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, onUnmounted } from 'vue'
import { scanAPI } from '../services/api'

export default {
  name: 'Scanner',
  setup() {
    const scanType = ref('ip')
    const ipAddress = ref('')
    const fileHash = ref('')
    const loading = ref(false)
    const error = ref('')
    const result = ref(null)
    
    // Auto-polling state
    const pollingEnabled = ref(false)
    const countdown = ref(60)
    let countdownInterval = null

    // Watch for scan type or target changes - stop polling
    watch(scanType, () => {
      stopPolling()
      result.value = null
    })

    watch([ipAddress, fileHash], () => {
      stopPolling()
    })

    const handleScan = async () => {
      error.value = ''
      result.value = null
      loading.value = true

      try {
        let response
        if (scanType.value === 'ip') {
          if (!ipAddress.value) {
            error.value = 'Please enter an IP address'
            return
          }
          response = await scanAPI.scanIP(ipAddress.value)
        } else {
          if (!fileHash.value) {
            error.value = 'Please enter a file hash'
            return
          }
          response = await scanAPI.scanHash(fileHash.value)
        }

        result.value = response.data.result
        
        // Start polling if enabled
        if (pollingEnabled.value) {
          startCountdown()
        }
      } catch (err) {
        error.value = err.response?.data?.detail || err.response?.data?.error || 'Scan failed'
        stopPolling()
      } finally {
        loading.value = false
      }
    }

    const startPolling = () => {
      pollingEnabled.value = true
      startCountdown()
    }

    const stopPolling = () => {
      pollingEnabled.value = false
      if (countdownInterval) {
        clearInterval(countdownInterval)
        countdownInterval = null
      }
      countdown.value = 60
    }

    const startCountdown = () => {
      countdown.value = 60
      
      if (countdownInterval) {
        clearInterval(countdownInterval)
      }
      
      countdownInterval = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) {
          rescan()
        }
      }, 1000)
    }

    const rescan = async () => {
      if (loading.value) return
      await handleScan()
    }

    const togglePolling = () => {
      if (pollingEnabled.value) {
        startCountdown()
      } else {
        stopPolling()
      }
    }

    onUnmounted(() => {
      stopPolling()
    })

    const formatDate = (dateString) => {
      if (!dateString) return 'N/A'
      try {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric'
        })
      } catch (e) {
        return dateString
      }
    }

    return {
      scanType,
      ipAddress,
      fileHash,
      loading,
      error,
      result,
      handleScan,
      pollingEnabled,
      countdown,
      togglePolling,
      formatDate
    }
  }
}
</script>

<style scoped>
.scanner-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.scanner-header {
  text-align: center;
  margin-bottom: 40px;
}

.scanner-header h1 {
  color: #FFD700;
  font-size: 2.5em;
  margin-bottom: 10px;
}

.scanner-header p {
  color: #CCC;
  font-size: 1.1em;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 30px;
}

.tab {
  flex: 1;
  padding: 15px;
  background: #1a1a1a;
  border: 2px solid #FFD700;
  color: #FFD700;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
}

.tab.active {
  background: #FFD700;
  color: #000;
}

.tab:hover:not(.active) {
  background: #2a2a2a;
}

.scanner-form {
  background: #1a1a1a;
  border: 3px solid #FFD700;
  padding: 30px;
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  color: #FFD700;
  margin-bottom: 10px;
  font-weight: bold;
  font-size: 1.1em;
}

input {
  width: 100%;
  padding: 15px;
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

.hint {
  color: #888;
  font-size: 0.9em;
  margin-top: 5px;
}

.btn-scan {
  width: 100%;
  padding: 18px;
  background: #FFD700;
  color: #000;
  border: none;
  font-size: 20px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-scan:hover:not(:disabled) {
  background: #FFA500;
  transform: translateY(-2px);
}

.btn-scan:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  background: #ff000020;
  border: 2px solid #ff0000;
  color: #ff6666;
  padding: 15px;
  margin-top: 20px;
  text-align: center;
}

.result-container {
  background: #1a1a1a;
  border: 3px solid #FFD700;
  padding: 30px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #FFD700;
}

.result-header h2 {
  color: #FFD700;
  font-size: 1.8em;
}

.badge {
  padding: 8px 16px;
  font-weight: bold;
  font-size: 1.1em;
}

.badge-danger {
  background: #ff0000;
  color: #FFF;
}

.badge-safe {
  background: #00ff00;
  color: #000;
}

.result-body {
  color: #FFF;
}

.result-item {
  margin-bottom: 20px;
  font-size: 1.1em;
}

.result-item strong {
  color: #FFD700;
  display: inline-block;
  min-width: 150px;
}

.threat-list {
  margin-top: 10px;
  margin-left: 150px;
  color: #ff6666;
}

.threat-list li {
  margin-bottom: 5px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 25px;
}

.stat-box {
  background: #000;
  border: 2px solid #FFD700;
  padding: 20px;
  text-align: center;
}

.stat-value {
  font-size: 2.5em;
  font-weight: bold;
  color: #FFD700;
  margin-bottom: 8px;
}

.stat-label {
  color: #CCC;
  font-size: 0.9em;
  text-transform: uppercase;
}

/* Engine Detection Details */
.engine-results {
  margin-top: 30px;
  background: #0a0a0a;
  border: 2px solid #FFD700;
  padding: 25px;
}

.engine-results h3 {
  color: #FFD700;
  font-size: 1.5em;
  margin-bottom: 10px;
}

.engine-count {
  color: #AAA;
  margin-bottom: 20px;
  font-size: 0.95em;
}

.engine-list {
  max-height: 500px;
  overflow-y: auto;
  border: 1px solid #333;
}

.engine-item {
  display: grid;
  grid-template-columns: 2fr 2fr 1fr;
  padding: 12px 15px;
  border-bottom: 1px solid #222;
  gap: 15px;
  align-items: center;
  transition: background 0.2s;
}

.engine-item:hover {
  background: rgba(255, 215, 0, 0.05);
}

.engine-item.category-malicious {
  background: rgba(255, 0, 0, 0.08);
  border-left: 4px solid #ff4444;
}

.engine-item.category-suspicious {
  background: rgba(255, 165, 0, 0.08);
  border-left: 4px solid #ffaa00;
}

.engine-item.category-undetected,
.engine-item.category-harmless {
  background: rgba(100, 100, 100, 0.05);
  border-left: 4px solid #555;
}

.engine-name {
  color: #FFF;
  font-weight: 500;
  font-size: 0.95em;
}

.engine-result {
  color: #CCC;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.engine-category {
  font-weight: bold;
  font-size: 0.85em;
  text-align: right;
  padding: 4px 8px;
  border-radius: 4px;
}

.engine-category.malicious {
  color: #ff4444;
  background: rgba(255, 0, 0, 0.15);
}

.engine-category.suspicious {
  color: #ffaa00;
  background: rgba(255, 165, 0, 0.15);
}

.engine-category.undetected,
.engine-category.harmless {
  color: #888;
  background: rgba(100, 100, 100, 0.15);
}

.engine-category.timeout {
  color: #666;
  background: rgba(100, 100, 100, 0.1);
}

/* WHOIS Information Styling */
.whois-section {
  background: #0a0a0a;
  border: 2px solid #FFD700;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
}

.whois-section h3 {
  color: #FFD700;
  margin-bottom: 15px;
  font-size: 1.3em;
}

.whois-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.whois-item {
  background: #1a1a1a;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #333;
}

.whois-item strong {
  color: #FFD700;
  display: block;
  margin-bottom: 5px;
  font-size: 0.9em;
}

.whois-item span {
  color: #FFF;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.whois-list {
  list-style: none;
  padding: 0;
  margin: 5px 0 0 0;
}

.whois-list li {
  color: #FFF;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  padding: 2px 0;
  margin-left: 15px;
}

.whois-note {
  margin-top: 15px;
  padding: 10px;
  background: #1a1a1a;
  border-radius: 4px;
  border-left: 4px solid #FFA500;
}

.whois-note small {
  color: #CCC;
  font-style: italic;
}

/* Scrollbar styling for engine list */
.engine-list::-webkit-scrollbar {
  width: 8px;
}

.engine-list::-webkit-scrollbar-track {
  background: #1a1a1a;
}

.engine-list::-webkit-scrollbar-thumb {
  background: #FFD700;
  border-radius: 4px;
}

.engine-list::-webkit-scrollbar-thumb:hover {
  background: #FFA500;
}

/* Auto-Polling Controls */
.polling-controls {
  margin-top: 25px;
  padding: 20px;
  background: #0a0a0a;
  border: 2px solid #FFD700;
}

.polling-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.polling-toggle {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.polling-toggle input[type="checkbox"] {
  width: 20px;
  height: 20px;
  margin-right: 12px;
  cursor: pointer;
  accent-color: #FFD700;
}

.toggle-label {
  color: #FFD700;
  font-size: 1.1em;
  font-weight: 500;
}

.countdown {
  color: #FFD700;
  font-size: 1.3em;
  font-weight: bold;
  animation: pulse 1s ease-in-out infinite;
}

.countdown strong {
  color: #FFA500;
  font-size: 1.2em;
}

.polling-info {
  color: #AAA;
  font-size: 0.9em;
  margin: 0;
  font-style: italic;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}
</style>

