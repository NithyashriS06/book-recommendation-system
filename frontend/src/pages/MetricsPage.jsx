import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { getMetrics, getPrecision } from '../services/api'
import { TrendingUp } from 'lucide-react'

export default function MetricsPage() {
  const [metrics, setMetrics] = useState([])
  const [precision, setPrecision] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getMetrics(500), getPrecision(10)])
      .then(([mRes, pRes]) => {
        setMetrics(mRes.data)
        setPrecision(pRes.data)
      })
      .catch(() => setError('Could not load metrics. Train the model first.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="page"><div className="loading">Loading metrics...</div></div>

  const statCards = [
    {
      label: 'Total Episodes',
      value: metrics.length > 0 ? metrics[metrics.length - 1]?.episode : 0,
      unit: '',
    },
    {
      label: 'Final ε (Epsilon)',
      value: metrics.length > 0 ? metrics[metrics.length - 1]?.epsilon?.toFixed(3) : '—',
      unit: '',
    },
    {
      label: 'Precision@10',
      value: precision?.precision_at_k != null
        ? `${(precision.precision_at_k * 100).toFixed(1)}`
        : '—',
      unit: '%',
    },
    {
      label: 'Logged Recommendations',
      value: precision?.sample_size ?? 0,
      unit: '',
    },
  ]

  return (
    <div className="page">
      <div className="page-title">Training Metrics</div>
      <div className="page-subtitle">DQN learning curves from offline simulation</div>

      {error && <div className="error-msg" style={{ marginBottom: '1rem' }}>{error}</div>}

      {/* Stat cards */}
      <div className="grid-2" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '1.5rem', gap: '0.75rem' }}>
        {statCards.map(({ label, value, unit }) => (
          <div key={label} className="card" style={{ padding: '1rem' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginBottom: '0.3rem' }}>{label}</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 700 }}>
              {value}{unit}
            </div>
          </div>
        ))}
      </div>

      {metrics.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--muted)' }}>
          <TrendingUp size={36} style={{ margin: '0 auto 1rem', display: 'block', opacity: 0.3 }} />
          No training data yet. Run <code>python scripts/train.py</code> to train the model.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* Cumulative Reward */}
          <div className="card">
            <div style={{ fontWeight: 600, marginBottom: '1.25rem', fontSize: '0.95rem' }}>
              Cumulative Reward per Episode
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={metrics} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="episode" tick={{ fontSize: 11, fill: 'var(--muted)' }} label={{ value: 'Episode', position: 'insideBottom', offset: -2, fill: 'var(--muted)', fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--muted)' }} />
                <Tooltip
                  contentStyle={{ fontSize: '0.82rem', borderColor: 'var(--border)', borderRadius: 6 }}
                  formatter={(v) => [v?.toFixed(3), 'Cumulative Reward']}
                />
                <Line type="monotone" dataKey="cumulative_reward" stroke="var(--amber)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Precision@K and Loss */}
          <div className="grid-2">
            <div className="card">
              <div style={{ fontWeight: 600, marginBottom: '1.25rem', fontSize: '0.95rem' }}>
                Precision@10 over Training
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={metrics} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="episode" tick={{ fontSize: 11, fill: 'var(--muted)' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--muted)' }} domain={[0, 1]} tickFormatter={v => `${(v*100).toFixed(0)}%`} />
                  <Tooltip
                    contentStyle={{ fontSize: '0.82rem', borderColor: 'var(--border)', borderRadius: 6 }}
                    formatter={(v) => [`${(v*100).toFixed(1)}%`, 'Precision@10']}
                  />
                  <Line type="monotone" dataKey="precision_at_k" stroke="var(--sage)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div style={{ fontWeight: 600, marginBottom: '1.25rem', fontSize: '0.95rem' }}>
                TD Loss + Epsilon Decay
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={metrics} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="episode" tick={{ fontSize: 11, fill: 'var(--muted)' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--muted)' }} />
                  <Tooltip contentStyle={{ fontSize: '0.82rem', borderColor: 'var(--border)', borderRadius: 6 }} />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: '0.8rem' }} />
                  <Line type="monotone" dataKey="loss" stroke="var(--rust)" strokeWidth={1.5} dot={false} name="TD Loss" />
                  <Line type="monotone" dataKey="epsilon" stroke="#8b9de8" strokeWidth={1.5} dot={false} name="Epsilon" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
