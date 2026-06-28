const BASE = '/api/v1'

const authHeaders = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${localStorage.getItem('token')}`
})

export const api = {
  // Auth
  register: (email, password, full_name) =>
    fetch(`${BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name })
    }).then(r => r.json()),

  login: (email, password) =>
    fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    }).then(r => r.json()),

  me: () =>
    fetch(`${BASE}/auth/me`, { headers: authHeaders() }).then(r => r.json()),

  wallet: () =>
    fetch(`${BASE}/auth/me/wallet`, { headers: authHeaders() }).then(r => r.json()),

  
  // Transactions
  deposit: (amount) =>
    fetch(`${BASE}/transactions/deposit`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ amount })
    }).then(r => r.json()),

  transfer: (receiver_email, amount) =>
    fetch(`${BASE}/transactions/transfer`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ receiver_email, amount })
    }).then(r => r.json()),

  history: (page = 1) =>
    fetch(`${BASE}/transactions/history?page=${page}`, {
      headers: authHeaders()
    }).then(r => r.json()),
}