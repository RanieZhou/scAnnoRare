import { defineStore } from 'pinia'
import axios from 'axios'

const WEB = 'http://127.0.0.1:8000'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token:    localStorage.getItem('scannorare_auth_token') || '',
    username: localStorage.getItem('scannorare_username')  || '',
    userId:   localStorage.getItem('scannorare_user_id')   || '',
    loggedIn: !!localStorage.getItem('scannorare_auth_token'),
  }),
  actions: {
    async login(username: string, password: string) {
      const res = await axios.post(`${WEB}/api/v1/auth/login`, { username, password })
      const { token, user } = res.data
      this.token    = token
      this.username = user.username
      this.userId   = user.id
      this.loggedIn = true
      localStorage.setItem('scannorare_auth_token', token)
      localStorage.setItem('scannorare_username',   user.username)
      localStorage.setItem('scannorare_user_id',    user.id)
    },
    async register(email: string, username: string, password: string) {
      await axios.post(`${WEB}/api/v1/auth/register`, { email, username, password })
    },
    logout() {
      this.token    = ''
      this.username = ''
      this.userId   = ''
      this.loggedIn = false
      localStorage.removeItem('scannorare_auth_token')
      localStorage.removeItem('scannorare_username')
      localStorage.removeItem('scannorare_user_id')
    },
    authHeader() {
      return this.token ? { Authorization: `Bearer ${this.token}` } : {}
    },
  },
})
