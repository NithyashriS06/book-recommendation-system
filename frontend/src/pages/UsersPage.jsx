import { useState, useEffect } from 'react'
import { getUsers, getUserRatings, getUserProfile } from '../services/api'
import BookCard from '../components/BookCard'
import { Users, ChevronRight } from 'lucide-react'

export default function UsersPage() {
  const [users, setUsers] = useState([])
  const [selected, setSelected] = useState(null)
  const [ratings, setRatings] = useState([])
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getUsers(100)
      .then(r => setUsers(r.data))
      .finally(() => setLoading(false))
  }, [])

  async function selectUser(user) {
    setSelected(user)
    const [rRes, pRes] = await Promise.all([
      getUserRatings(user.id, 20),
      getUserProfile(user.id),
    ])
    setRatings(rRes.data)
    setProfile(pRes.data)
  }

  return (
    <div className="page">
      <div className="page-title">Users</div>
      <div className="page-subtitle">Browse users and their reading history</div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '1.5rem' }}>
        {/* User list */}
        <div className="card" style={{ padding: '0', overflow: 'hidden', alignSelf: 'start', maxHeight: '80vh', overflowY: 'auto' }}>
          {loading && <div className="loading">Loading...</div>}
          {users.map(u => (
            <button
              key={u.id}
              onClick={() => selectUser(u)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '0.75rem 1rem', borderBottom: '1px solid var(--border)',
                background: selected?.id === u.id ? 'var(--cream)' : 'white',
                fontFamily: 'var(--font-body)', fontSize: '0.88rem', color: 'var(--ink)',
                textAlign: 'left', cursor: 'pointer',
                transition: 'background 0.1s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: selected?.id === u.id ? 'var(--amber)' : 'var(--cream)',
                  color: selected?.id === u.id ? 'white' : 'var(--muted)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.72rem', fontWeight: 700, flexShrink: 0,
                }}>
                  {u.goodreads_user_id % 100}
                </div>
                User #{u.goodreads_user_id}
              </div>
              {selected?.id === u.id && <ChevronRight size={14} color="var(--amber)" />}
            </button>
          ))}
        </div>

        {/* User detail */}
        <div>
          {selected ? (
            <>
              {/* Genre profile */}
              {profile && (
                <div className="card" style={{ marginBottom: '1rem' }}>
                  <div style={{ fontWeight: 600, marginBottom: '0.75rem', fontSize: '0.92rem' }}>
                    Genre Profile — User #{selected.goodreads_user_id}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.5rem' }}>
                    {Object.entries(profile.genre_profile)
                      .sort((a, b) => b[1] - a[1])
                      .map(([genre, avg]) => (
                        <span key={genre} className="badge badge-amber" style={{ textTransform: 'capitalize' }}>
                          {genre}: {avg}★
                        </span>
                      ))}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                    {profile.total_ratings} books rated
                  </div>
                </div>
              )}

              {/* Ratings */}
              <div style={{ fontWeight: 600, marginBottom: '0.6rem', fontSize: '0.92rem' }}>
                Recently Rated Books (top 20)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {ratings.map(r => (
                  <BookCard key={r.book_id} book={r} userRating={r.rating} />
                ))}
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--muted)' }}>
              <Users size={36} style={{ margin: '0 auto 1rem', display: 'block', opacity: 0.3 }} />
              Select a user from the list
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
