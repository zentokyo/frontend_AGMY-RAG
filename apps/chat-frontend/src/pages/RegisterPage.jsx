import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import useAuthStore from '../store/authStore.js'

export default function RegisterPage() {
  const navigate = useNavigate()
  const register = useAuthStore((s) => s.register)
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await register(email, password, username)
      toast.success('Регистрация завершена')
      navigate('/app', { replace: true })
    } catch (err) {
      toast.error(err.response?.data?.error || 'Не удалось зарегистрироваться')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-100 px-4 py-12">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 shadow-lg">
          <span className="text-2xl font-bold text-white">A</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Регистрация</h1>
        <p className="mt-1 text-sm text-slate-500">Создание учётной записи</p>
      </div>
      <div className="card w-full max-w-md p-8">
        <form className="space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="label" htmlFor="username">Имя</label>
            <input
              id="username"
              type="text"
              className="input"
              placeholder="Иван"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              className="input"
              placeholder="user@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="password">Пароль</label>
            <input
              id="password"
              type="password"
              className="input"
              placeholder="Минимум 6 символов"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>
          <button type="submit" className="btn-primary w-full justify-center" disabled={loading}>
            {loading ? 'Создание...' : 'Создать аккаунт'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-500">
          Уже есть аккаунт? <Link className="text-blue-600 hover:underline" to="/login">Войти</Link>
        </p>
      </div>
    </div>
  )
}
