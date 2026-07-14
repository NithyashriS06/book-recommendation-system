import { NavLink } from 'react-router-dom'
import { BookOpen, Users, Star, BarChart2, Search } from 'lucide-react'

const links = [
  { to: '/',              icon: Star,     label: 'Recommendations' },
  { to: '/users',         icon: Users,    label: 'Users'           },
  { to: '/books',         icon: Search,   label: 'Browse Books'    },
  { to: '/metrics',       icon: BarChart2,label: 'Training Metrics'},
]

export default function Sidebar() {
  return (
    <aside style={{
      width: 220,
      minHeight: '100vh',
      background: 'var(--ink)',
      display: 'flex',
      flexDirection: 'column',
      padding: '1.5rem 0',
      flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{ padding: '0 1.25rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <BookOpen size={22} color="var(--amber-light)" />
          <div>
            <div style={{ fontFamily: 'var(--font-display)', color: 'white', fontSize: '1rem', fontWeight: 700, lineHeight: 1.2 }}>
              BookRL
            </div>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem' }}>DQN Recommender</div>
          </div>
        </div>
      </div>

      {/* Nav links */}
      <nav style={{ marginTop: '1rem', flex: 1 }}>
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '0.7rem',
              padding: '0.65rem 1.25rem',
              color: isActive ? 'var(--amber-light)' : 'rgba(255,255,255,0.55)',
              fontSize: '0.88rem',
              fontWeight: 500,
              borderLeft: isActive ? '3px solid var(--amber)' : '3px solid transparent',
              background: isActive ? 'rgba(196,137,42,0.08)' : 'transparent',
              transition: 'all 0.15s',
            })}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '1rem 1.25rem', color: 'rgba(255,255,255,0.25)', fontSize: '0.72rem' }}>
        Research prototype<br />localhost only
      </div>
    </aside>
  )
}
