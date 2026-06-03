import { defineStore } from 'pinia'
import axios from 'axios'

export const useAgentStore = defineStore('agent', {
  state: () => ({
    sessionToken: localStorage.getItem('scannorare_session_token') || '',
    paired: !!localStorage.getItem('scannorare_session_token'),
    agentUrl: 'http://127.0.0.1:17890',
    webOrigin: window.location.origin || 'http://localhost:5173',
    envInfo: null as any,
    isOnline: false
  }),
  actions: {
    setPairing(token: string) {
      this.sessionToken = token
      this.paired = true
      localStorage.setItem('scannorare_session_token', token)
    },
    unpair() {
      this.sessionToken = ''
      this.paired = false
      this.envInfo = null
      this.isOnline = false
      localStorage.removeItem('scannorare_session_token')
    },
    async checkAgentHealth() {
      try {
        const res = await axios.get(`${this.agentUrl}/api/v1/local/health`, {
          timeout: 2000
        })
        this.isOnline = true
        this.paired = res.data.paired
        if (!this.paired && this.sessionToken) {
          // Token expired on Agent restart
          this.unpair()
        }
        return true
      } catch (err) {
        this.isOnline = false
        return false
      }
    },
    async fetchAgentEnv() {
      if (!this.paired || !this.isOnline) return
      
      try {
        const res = await axios.get(`${this.agentUrl}/api/v1/local/env`, {
          headers: {
            'Authorization': `Bearer ${this.sessionToken}`,
            'X-scAnnoRare-Origin': this.webOrigin
          }
        })
        this.envInfo = res.data
      } catch (err) {
        console.error('Failed to fetch Agent environment specs:', err)
      }
    }
  }
})
