import useAuthStore from '../store/authStore.js'

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user)

  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">Профиль</h1>
      <div className="card mt-4 p-4 space-y-1 text-sm text-slate-700">
        <p><span className="text-slate-500">ID:</span> {user?.id ?? '—'}</p>
        <p><span className="text-slate-500">Email:</span> {user?.email ?? '—'}</p>
        <p><span className="text-slate-500">Имя:</span> {user?.username || '—'}</p>
      </div>
    </div>
  )
}
