import { User } from 'lucide-react'
import type { AdminUser } from '../types'
import { useLang } from '../i18n'

export function AdminPanel({
  users,
  onToggleUser,
}: {
  users: AdminUser[]
  onToggleUser: (email: string, disable: boolean) => void
}) {
  const { t } = useLang()
  return (
    <section className="admin-panel">
      <div className="panel-heading compact">
        <User size={18} />
        <h2>{t.admin.heading} ({users.length})</h2>
      </div>
      {users.length === 0 ? (
        <div className="audit-empty">{t.admin.none}</div>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t.admin.email}</th>
              <th>{t.admin.tenant}</th>
              <th>{t.admin.role}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.email} className={u.disabled ? 'admin-row-disabled' : ''}>
                <td>{u.email}</td>
                <td><span className="tenant-badge" style={{ fontSize: '0.75rem' }}>{u.tenant_id}</span></td>
                <td><span className={`role-badge ${u.role}`}>{u.role}</span></td>
                <td>
                  <button
                    type="button"
                    className={u.disabled ? 'admin-toggle-btn enable' : 'admin-toggle-btn disable'}
                    onClick={() => onToggleUser(u.email, !u.disabled)}
                    title={u.disabled ? t.admin.reactivate : t.admin.deactivate}
                  >
                    {u.disabled ? t.admin.enable : t.admin.disable}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
