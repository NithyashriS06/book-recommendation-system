const FALLBACK = 'https://via.placeholder.com/60x90/e8e0d0/7a7060?text=Book'

function Stars({ rating }) {
  return (
    <span>
      {'★'.repeat(Math.round(rating))}{'☆'.repeat(5 - Math.round(rating))}
    </span>
  )
}

export default function BookCard({ book, rank, qValue, userRating }) {
  return (
    <div style={{
      display: 'flex',
      gap: '1rem',
      padding: '1rem',
      background: 'white',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      boxShadow: 'var(--shadow)',
      transition: 'box-shadow 0.15s',
    }}
    onMouseEnter={e => e.currentTarget.style.boxShadow = 'var(--shadow-lg)'}
    onMouseLeave={e => e.currentTarget.style.boxShadow = 'var(--shadow)'}
    >
      {/* Rank */}
      {rank && (
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: rank <= 3 ? 'var(--amber)' : 'var(--cream)',
          color: rank <= 3 ? 'white' : 'var(--muted)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '0.78rem', fontWeight: 700, flexShrink: 0,
        }}>
          {rank}
        </div>
      )}

      {/* Cover */}
      <img
        src={book.image_url || FALLBACK}
        alt={book.title}
        onError={e => { e.target.src = FALLBACK }}
        style={{ width: 48, height: 72, objectFit: 'cover', borderRadius: 3, flexShrink: 0 }}
      />

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 600,
          fontSize: '0.95rem',
          lineHeight: 1.3,
          marginBottom: '0.2rem',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {book.title}
        </div>
        <div style={{ color: 'var(--muted)', fontSize: '0.82rem', marginBottom: '0.4rem' }}>
          {book.authors}
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
          {book.average_rating && (
            <span style={{ color: 'var(--amber)', fontSize: '0.82rem' }}>
              ★ {book.average_rating?.toFixed(1)}
            </span>
          )}
          {qValue !== undefined && (
            <span className="badge badge-amber">Q: {qValue.toFixed(3)}</span>
          )}
          {userRating && (
            <span className="badge badge-sage">You rated: {userRating}★</span>
          )}
        </div>
      </div>
    </div>
  )
}
