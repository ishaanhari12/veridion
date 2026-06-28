import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../services/api'

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [transactions, setTransactions] = useState([])
  const [balance, setBalance] = useState(null)
  const [loading, setLoading] = useState(true)

  // Deposit form
  const [depositAmount, setDepositAmount] = useState('')
  // Transfer form
  const [transferEmail, setTransferEmail] = useState('')
  const [transferAmount, setTransferAmount] = useState('')
  const [message, setMessage] = useState('')

  const loadData = async () => {
    const [wallet, hist] = await Promise.all([api.wallet(), api.history()])
    setBalance(wallet.balance)
    setTransactions(hist.items || [])
    setLoading(false)
  }

  useEffect(() => { loadData() }, [])

  const handleDeposit = async (e) => {
    e.preventDefault()
    await api.deposit(parseFloat(depositAmount))
    setDepositAmount('')
    setMessage('Deposit successful')
    loadData()
  }

  const handleTransfer = async (e) => {
    e.preventDefault()
    const result = await api.transfer(transferEmail, parseFloat(transferAmount))
    if (result.status === 'blocked') {
      setMessage('Transfer blocked — high fraud risk detected')
    } else if (result.status === 'flagged') {
      setMessage(`Transfer flagged for review (fraud score: ${result.fraud_score})`)
    } else {
      setMessage('Transfer completed successfully')
    }
    setTransferEmail('')
    setTransferAmount('')
    loadData()
  }

  const fraudColour = (score) => {
    if (!score) return 'text-gray-500'
    if (score >= 0.85) return 'text-red-400'
    if (score >= 0.50) return 'text-yellow-400'
    return 'text-green-400'
  }

  if (loading) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <p className="text-gray-400">Loading...</p>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold">Veridion</h1>
          <p className="text-gray-400 text-sm">Welcome, {user.full_name}</p>
        </div>
        <button onClick={logout} className="text-gray-400 hover:text-white text-sm">
          Sign out
        </button>
      </div>

      {/* Balance */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 mb-6">
        <p className="text-gray-400 text-sm mb-1">Wallet Balance</p>
        <p className="text-4xl font-bold">£{parseFloat(balance || 0).toFixed(2)}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-4 text-center">
          <p className="text-2xl font-bold">{transactions.length}</p>
          <p className="text-gray-400 text-xs mt-1">Total Transactions</p>
        </div>
        <div className="bg-gray-900 border border-yellow-900 rounded-2xl p-4 text-center">
          <p className="text-2xl font-bold text-yellow-400">
            {transactions.filter(t => t.status === 'flagged').length}
          </p>
          <p className="text-gray-400 text-xs mt-1">Flagged</p>
        </div>
        <div className="bg-gray-900 border border-red-900 rounded-2xl p-4 text-center">
          <p className="text-2xl font-bold text-red-400">
            {transactions.filter(t => t.status === 'blocked').length}
          </p>
          <p className="text-gray-400 text-xs mt-1">Blocked</p>
        </div>
      </div>

      {message && (
        <div className="bg-blue-900 border border-blue-700 rounded-lg p-3 mb-6 text-sm">
          {message}
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Deposit */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="font-semibold mb-4">Deposit Funds</h2>
          <form onSubmit={handleDeposit} className="space-y-3">
            <input
              type="number"
              placeholder="Amount (£)"
              value={depositAmount}
              onChange={e => setDepositAmount(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              required
            />
            <button type="submit" className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg px-4 py-3 transition">
              Deposit
            </button>
          </form>
        </div>

        {/* Transfer */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="font-semibold mb-4">Send Money</h2>
          <form onSubmit={handleTransfer} className="space-y-3">
            <input
              type="email"
              placeholder="Recipient email"
              value={transferEmail}
              onChange={e => setTransferEmail(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              required
            />
            <input
              type="number"
              placeholder="Amount (£)"
              value={transferAmount}
              onChange={e => setTransferAmount(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              required
            />
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg px-4 py-3 transition">
              Send
            </button>
          </form>
        </div>
      </div>

      {/* Transaction History */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
        <h2 className="font-semibold mb-4">Transaction History</h2>
        {transactions.length === 0 ? (
          <p className="text-gray-500 text-sm">No transactions yet</p>
        ) : (
          <div className="space-y-3">
            {transactions.map(tx => (
              <div key={tx.id} className="flex justify-between items-center border-b border-gray-800 pb-3">
                <div>
                  <p className="text-sm font-medium capitalize">{tx.transaction_type}</p>
                  <p className="text-xs text-gray-500">{new Date(tx.created_at).toLocaleString()}</p>
                  {tx.fraud_score && (
                    <p className={`text-xs ${fraudColour(tx.fraud_score)}`}>
                      Fraud score: {tx.fraud_score}
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <p className="font-semibold">£{parseFloat(tx.amount).toFixed(2)}</p>
                  <p className={`text-xs capitalize ${tx.status === 'blocked' ? 'text-red-400' : tx.status === 'flagged' ? 'text-yellow-400' : 'text-green-400'}`}>
                    {tx.status}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}