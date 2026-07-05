import { User } from 'lucide-react'
import type { AdminUser } from '../types'

export function AdminPanel({
  users,
  onToggleUser,
}: {
  users: AdminUser[]
  onToggleUser: (email: string, disable: boolean) => void
}) {
  return (
    <section className="admin-panel">
      <div className="panel-heading compact">
        <User size={18} />
        <h2>Utilisateurs ({users.length})</h2>
      </div>
      {users.length === 0 ? (
        <div className="audit-empty">Aucun utilisateur charge.</div>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Tenant</th>
              <th>Role</th>
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
                    title={u.disabled ? 'Réactiver' : 'Désactiver'}
                  >
                    {u.disabled ? 'Activer' : 'Désactiver'}
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
