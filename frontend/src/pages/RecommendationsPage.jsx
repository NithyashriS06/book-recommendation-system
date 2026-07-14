import { useState, useEffect } from 'react'
import { getUsers, getRecommendations, getUserProfile, getPrecision } from '../services/api'
import BookCard from '../components/BookCard'
import { Sparkles, User, Target } from 'lucide-react'

export default function RecommendationsPage() {
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState('')
  const [recs, setRecs] = useState(null)
  const [profile, setProfile] = useState(null)
  const [precision, setPrecision] = useState(null)
  const [topK, setTopK] = useState(10)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getUsers(100).then(r => setUsers(r.data)).catch(() => {})
  }, [])

  async function fetchRecs() {
    if (!selectedUser) return
    setLoading(true)
    setError('')
    try {
      const [recRes, profRes, precRes] = await Promise.all([
        getRecommendations(selectedUser, topK),
        getUserProfile(selectedUser),
        getPrecision(topK),
      ])
      setRecs(recRes.data)
      setProfile(profRes.data)
      setPrecision(precRes.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to fetch recommendations. Is the model trained?')
    }
    setLoading(false)
  }

  const topGenres = profile?.genre_profile
    ? Object.entries(profile.genre_profile)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
    : []

  return (
    <div className="page">
      <div className="page-title">Book Recommendations</div>
      <div className="page-subtitle">DQN agent suggests books based on your genre profile</div>

      {/* Controls */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--muted)', marginBottom: '0.35rem' }}>
              Select User
            </label>
            <select
              value={selectedUser}
              onChange={e => { setSelectedUser(e.target.value); setRecs(null); setProfile(null) }}
              style={{
                width: '100%', padding: '0.5rem 0.75rem',
                border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                background: 'white', fontFamily: 'var(--font-body)', fontSize: '0.9rem',
              }}
            >
              <option value="">— choose a user —</option>
              {users.map(u => (
                <option key={u.id} value={u.id}>User #{u.goodreads_user_id}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--muted)', marginBottom: '0.35rem' }}>
              Top K
            </label>
            <select
              value={topK}
              onChange={e => setTopK(Number(e.target.value))}
              style={{
                padding: '0.5rem 0.75rem',
                border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                background: 'white', fontFamily: 'var(--font-body)', fontSize: '0.9rem',
              }}
            >
              {[5, 10, 20].map(k => <option key={k} value={k}>{k} books</option>)}
            </select>
          </div>

          <button
            className="btn btn-primary"
            onClick={fetchRecs}
            disabled={!selectedUser || loading}
            style={{ opacity: (!selectedUser || loading) ? 0.6 : 1 }}
          >
            <Sparkles size={15} />
            {loading ? 'Loading...' : 'Get Recommendations'}
          </button>
        </div>
      </div>

      {error && <div className="error-msg" style={{ marginBottom: '1rem' }}>{error}</div>}

      {profile && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
          {/* Genre profile */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <User size={16} color="var(--amber)" />
              <span style={{ fontWeight: 600, fontSize: '0.92rem' }}>Genre Profile (RL State)</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {topGenres.map(([genre, avg]) => (
                <div key={genre} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ width: 130, fontSize: '0.82rem', color: 'var(--muted)', textTransform: 'capitalize' }}>
                    {genre}
                  </span>
                  <div style={{ flex: 1, height: 6, background: 'var(--cream)', borderRadius: 3 }}>
                    <div style={{
                      width: `${(avg / 5) * 100}%`,
                      height: '100%',
                      background: 'var(--amber)',
                      borderRadius: 3,
                    }} />
                  </div>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--amber-dark)', width: 30 }}>
                    {avg}
                  </span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--muted)' }}>
              Based on {profile.total_ratings} rated books
            </div>
          </div>

          {/* Precision@K */}
          {precision && (
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                <Target size={16} color="var(--sage)" />
                <span style={{ fontWeight: 600, fontSize: '0.92rem' }}>Evaluation Metrics</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginBottom: '0.2rem' }}>
                    Precision@{precision.k}
                  </div>
                  <div style={{ fontSize: '1.8rem', fontFamily: 'var(--font-display)', fontWeight: 700, color: 'var(--ink)' }}>
                    {precision.precision_at_k !== null
                      ? `${(precision.precision_at_k * 100).toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>
                    Rated ≥4★ out of {precision.sample_size} logged recs
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginBottom: '0.2rem' }}>Threshold</div>
                  <span className="badge badge-amber">≥ {precision.threshold} stars</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Recommendations list */}
      {recs && (
        <div>
          <div style={{ fontWeight: 600, marginBottom: '0.75rem', fontSize: '0.95rem' }}>
            Top {recs.recommendations.length} Recommendations
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {recs.recommendations.map(rec => (
              <BookCard
                key={rec.book_id}
                book={rec}
                rank={rec.rank}
                qValue={rec.q_value}
                userRating={rec.actual_user_rating}
              />
            ))}
          </div>
        </div>
      )}

      {!recs && !loading && (
        <div style={{
          textAlign: 'center', padding: '4rem 2rem',
          color: 'var(--muted)', fontSize: '0.95rem',
        }}>
          <Sparkles size={32} style={{ margin: '0 auto 1rem', display: 'block', opacity: 0.3 }} />
          Select a user and click "Get Recommendations" to see DQN predictions
        </div>
      )}
    </div>
  )
}
