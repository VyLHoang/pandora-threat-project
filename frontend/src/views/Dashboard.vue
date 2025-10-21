<template>
  <div class="dashboard-container">
    <h1>📊 Dashboard</h1>
    
    <div class="stats-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-number">{{ stats.total_scans || 0 }}</div>
        <div class="stat-label">Total Scans</div>
      </div>
      <div class="stat-card threat-card">
        <div class="stat-number">{{ stats.malicious_count || 0 }}</div>
        <div class="stat-label">Threats Found</div>
      </div>
      <div class="stat-card clean-card">
        <div class="stat-number">{{ stats.clean_count || 0 }}</div>
        <div class="stat-label">Clean Results</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.suspicious_count || 0 }}</div>
        <div class="stat-label">Suspicious</div>
      </div>
    </div>

    <!-- Charts Section -->
    <div class="charts-grid" v-if="stats">
      <div class="chart-box">
        <h2>🎯 Threat Distribution</h2>
        <canvas ref="maliciousChart"></canvas>
      </div>
      
      <div class="chart-box">
        <h2>📈 Scan Trend (7 Days)</h2>
        <canvas ref="scanTrendChart"></canvas>
      </div>
    </div>

    <div class="quick-actions">
      <h2>⚡ Quick Actions</h2>
      <div class="action-buttons">
        <router-link to="/scanner" class="action-btn">
          🔍 New Scan
        </router-link>
        <router-link to="/history" class="action-btn">
          📜 View History
        </router-link>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { Chart, registerables } from 'chart.js'
import { historyAPI } from '../services/api'

Chart.register(...registerables)

export default {
  name: 'Dashboard',
  setup() {
    const stats = ref(null)
    const maliciousChart = ref(null)
    const scanTrendChart = ref(null)
    let pieChart = null
    let lineChart = null

    const loadStats = async () => {
      try {
        const response = await historyAPI.getStats()
        stats.value = response.data
        
        // Initialize charts after data is loaded
        setTimeout(() => {
          initCharts()
        }, 100)
      } catch (err) {
        console.error('Failed to load stats:', err)
        // Use default data if stats fail
        stats.value = {
          total_scans: 0,
          malicious_count: 0,
          clean_count: 0,
          suspicious_count: 0,
          daily_scans: []
        }
      }
    }

    const initCharts = () => {
      if (!stats.value) return

      // Malicious vs Clean Pie Chart
      if (maliciousChart.value) {
        const pieCtx = maliciousChart.value.getContext('2d')
        
        if (pieChart) {
          pieChart.destroy()
        }
        
        pieChart = new Chart(pieCtx, {
          type: 'doughnut',
          data: {
            labels: ['Malicious', 'Clean', 'Suspicious'],
            datasets: [{
              data: [
                stats.value.malicious_count || 0,
                stats.value.clean_count || 0,
                stats.value.suspicious_count || 0
              ],
              backgroundColor: ['#ff4444', '#44ff44', '#ffaa00'],
              borderColor: '#000',
              borderWidth: 2
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  color: '#fff',
                  font: { size: 14 },
                  padding: 15
                }
              },
              title: {
                display: false
              }
            }
          }
        })
      }
      
      // Scan trend over time (last 7 days)
      if (scanTrendChart.value && stats.value.daily_scans) {
        const lineCtx = scanTrendChart.value.getContext('2d')
        
        if (lineChart) {
          lineChart.destroy()
        }
        
        lineChart = new Chart(lineCtx, {
          type: 'line',
          data: {
            labels: stats.value.daily_scans.map(d => d.date),
            datasets: [{
              label: 'Scans per Day',
              data: stats.value.daily_scans.map(d => d.count),
              borderColor: '#FFD700',
              backgroundColor: 'rgba(255, 215, 0, 0.1)',
              tension: 0.4,
              fill: true,
              borderWidth: 3,
              pointBackgroundColor: '#FFD700',
              pointBorderColor: '#000',
              pointBorderWidth: 2,
              pointRadius: 5,
              pointHoverRadius: 7
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
              legend: {
                display: false
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  color: '#fff',
                  font: { size: 12 },
                  stepSize: 1
                },
                grid: {
                  color: '#333'
                }
              },
              x: {
                ticks: {
                  color: '#fff',
                  font: { size: 12 }
                },
                grid: {
                  color: '#333'
                }
              }
            }
          }
        })
      }
    }

    onMounted(() => {
      loadStats()
    })

    return { 
      stats,
      maliciousChart,
      scanTrendChart
    }
  }
}
</script>

<style scoped>
.dashboard-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  color: #FFD700;
  font-size: 2.5em;
  margin-bottom: 30px;
  text-align: center;
}

h2 {
  color: #FFD700;
  font-size: 1.4em;
  margin-bottom: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.stat-card {
  background: #1a1a1a;
  border: 3px solid #FFD700;
  padding: 30px;
  text-align: center;
  transition: all 0.3s;
}

.stat-card.threat-card {
  border-color: #ff4444;
}

.stat-card.clean-card {
  border-color: #44ff44;
}

.stat-card:hover {
  background: #FFD700;
  color: #000;
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(255, 215, 0, 0.3);
}

.stat-card.threat-card:hover {
  background: #ff4444;
  color: #fff;
}

.stat-card.clean-card:hover {
  background: #44ff44;
  color: #000;
}

.stat-number {
  font-size: 3em;
  font-weight: bold;
  color: #FFD700;
  margin-bottom: 10px;
}

.stat-card:hover .stat-number {
  color: #000;
}

.stat-card.threat-card .stat-number {
  color: #ff4444;
}

.stat-card.clean-card .stat-number {
  color: #44ff44;
}

.stat-card.threat-card:hover .stat-number,
.stat-card.clean-card:hover .stat-number {
  color: #000;
}

.stat-label {
  font-size: 1em;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Charts Section */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 30px;
  margin-bottom: 40px;
}

.chart-box {
  background: #1a1a1a;
  border: 3px solid #FFD700;
  padding: 25px;
  min-height: 350px;
}

.chart-box h2 {
  text-align: center;
  margin-bottom: 25px;
  font-size: 1.3em;
}

.chart-box canvas {
  max-height: 300px;
}

.quick-actions {
  background: #1a1a1a;
  border: 3px solid #FFD700;
  padding: 30px;
}

.action-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.action-btn {
  padding: 20px;
  background: #FFD700;
  color: #000;
  text-align: center;
  text-decoration: none;
  font-size: 1.3em;
  font-weight: bold;
  transition: all 0.3s;
  border-radius: 5px;
}

.action-btn:hover {
  background: #FFA500;
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(255, 165, 0, 0.4);
}

/* Responsive */
@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
  
  h1 {
    font-size: 2em;
  }
  
  .stat-number {
    font-size: 2.5em;
  }
}
</style>

