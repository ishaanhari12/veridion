import { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      api.me().then(data => {
        if (data.email) setUser(data)
        else localStorage.removeItem('token')
      }).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email, password) => {
    const data = await api.login(email, password)
    if (data.access_token) {
      localStorage.setItem('token', data.access_token)
      const me = await api.me()
      setUser(me)
      return { success: true }
    }
    return { success: false, error: data.detail }
  }

  const register = async (email, password, full_name) => {
    const data = await api.register(email, password, full_name)
    if (data.access_token) {
      localStorage.setItem('token', data.access_token)
      const me = await api.me()
      setUser(me)
      return { success: true }
    }
    return { success: false, error: data.detail }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)