import { defineStore } from 'pinia'
import axios from 'axios'

export const useAgentStore = defineStore('agent', {
  state: () => ({
    sessionToken: localStorage.getItem('scannorare_session_token') || '',
    paired:       !!localStorage.getItem('scannorare_session_token'),
    agentUrl:     'http://127.0.0.1:17890',
    webOrigin:    window.location.origin || 'http://localhost:5173',
    envInfo:      null as any,
    isOnline:     false,
  }),

  actions: {
    setPairing(token: string) {
      this.sessionToken = token
      this.paired       = true
      localStorage.setItem('scannorare_session_token', token)
    },

    unpair() {
      this.sessionToken = ''
      this.paired       = false
      this.envInfo      = null
      this.isOnline     = false
      localStorage.removeItem('scannorare_session_token')
    },

    /** Check agent liveness and sync paired state. Returns true if online. */
    async checkAgentHealth(): Promise<boolean> {
      try {
        const res = await axios.get(`${this.agentUrl}/api/v1/local/health`, { timeout: 3000 })
        this.isOnline = true

        const agentPaired: boolean = res.data.paired

        if (!agentPaired && this.sessionToken) {
          // Agent restarted — our stored token is invalid
          this.unpair()
          return true
        }

        if (agentPaired && this.sessionToken && !this.envInfo) {
          // Paired and token present but envInfo missing — load it now
          await this.fetchAgentEnv()
        }

        return true
      } catch {
        this.isOnline = false
        return false
      }
    },

    /** Fetch environment info from agent. Unpairs if token is rejected. */
    async fetchAgentEnv() {
      if (!this.sessionToken) return

      try {
        const res = await axios.get(`${this.agentUrl}/api/v1/local/env`, {
          headers: {
            Authorization: `Bearer ${this.sessionToken}`,
            'X-scAnnoRare-Origin': this.webOrigin,
          },
          timeout: 5000,
        })
        this.envInfo = res.data
      } catch (err: any) {
        if (err?.response?.status === 401) {
          // Token rejected — clear stale auth
          this.unpair()
        }
      }
    },

    authHeaders() {
      return {
        Authorization: `Bearer ${this.sessionToken}`,
        'X-scAnnoRare-Origin': this.webOrigin,
      }
    },
  },
})
