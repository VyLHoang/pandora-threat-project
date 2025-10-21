<template>
  <div class="history-container">
    <h1>Scan History</h1>
    
    <div v-if="loading" class="loading">Loading...</div>
    
    <div v-else-if="scans.length === 0" class="empty-state">
      <p>No scans yet. Start scanning to see your history!</p>
      <router-link to="/scanner" class="btn-primary">Go to Scanner</router-link>
    </div>
    
    <div v-else class="scans-list">
      <div v-for="scan in scans" :key="scan.id" class="scan-item">
        <div class="scan-header">
          <span class="scan-type">{{ scan.scan_type.toUpperCase() }}</span>
          <span class="scan-target">{{ scan.target }}</span>
          <span :class="['scan-status', `status-${scan.status}`]">
            {{ scan.status }}
          </span>
        </div>
        <div class="scan-details">
          <div>
            <strong>Date:</strong> {{ formatDate(scan.created_at) }}
          </div>
          <div v-if="scan.is_malicious !== null">
            <strong>Result:</strong>
            <span :class="scan.is_malicious ? 'text-danger' : 'text-safe'">
              {{ scan.is_malicious ? '⚠️ Malicious' : '✅ Safe' }}
            </span>
          </div>
          <div v-if="scan.detection_count !== null">
            <strong>Detection:</strong> {{ scan.detection_count }} threats found
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { historyAPI } from '../services/api'

export default {
  name: 'History',
  setup() {
    const scans = ref([])
    const loading = ref(true)

    const loadHistory = async () => {
      try {
        const response = await historyAPI.getHistory({ limit: 50 })
        scans.value = response.data.scans
      } catch (err) {
        console.error('Failed to load history:', err)
      } finally {
        loading.value = false
      }
    }

    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleString()
    }

    onMounted(() => {
      loadHistory()
    })

    return {
      scans,
      loading,
      formatDate
    }
  }
}
</script>

<style scoped>
.history-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  color: #FFD700;
  font-size: 2.5em;
  margin-bottom: 30px;
}

.loading, .empty-state {
  text-align: center;
  color: #FFD700;
  font-size: 1.5em;
  padding: 40px;
}

.btn-primary {
  display: inline-block;
  margin-top: 20px;
  padding: 15px 30px;
  background: #FFD700;
  color: #000;
  text-decoration: none;
  font-weight: bold;
}

.scans-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.scan-item {
  background: #1a1a1a;
  border: 2px solid #FFD700;
  padding: 20px;
}

.scan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #FFD700;
}

.scan-type {
  background: #FFD700;
  color: #000;
  padding: 5px 10px;
  font-weight: bold;
  font-size: 0.9em;
}

.scan-target {
  color: #FFF;
  font-size: 1.1em;
  font-weight: bold;
  flex: 1;
  margin: 0 15px;
}

.scan-status {
  padding: 5px 10px;
  font-size: 0.9em;
  font-weight: bold;
}

.status-completed {
  background: #00ff00;
  color: #000;
}

.status-pending, .status-processing {
  background: #FFA500;
  color: #000;
}

.status-failed {
  background: #ff0000;
  color: #FFF;
}

.scan-details {
  display: flex;
  gap: 30px;
  color: #CCC;
}

.scan-details strong {
  color: #FFD700;
}

.text-danger {
  color: #ff6666;
  font-weight: bold;
}

.text-safe {
  color: #66ff66;
  font-weight: bold;
}
</style>

