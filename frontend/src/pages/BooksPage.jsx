import { useState, useEffect, useRef } from 'react'
import { getBooks } from '../services/api'
import BookCard from '../components/BookCard'
import { Search } from 'lucide-react'

export default function BooksPage() {
  const [query, setQuery] = useState('')
  const [books, setBooks] = useState([])
  const [loading, setLoading] = useState(false)
  const debounce = useRef(null)

  useEffect(() => {
    // Initial load
    fetchBooks('')
  }, [])

  function fetchBooks(q) {
    setLoading(true)
    getBooks(q, 30)
      .then(r => setBooks(r.data))
      .finally(() => setLoading(false))
  }

  function onSearch(e) {
    const val = e.target.value
    setQuery(val)
    clearTimeout(debounce.current)
    debounce.current = setTimeout(() => fetchBooks(val), 400)
  }

  return (
    <div className="page">
      <div className="page-title">Browse Books</div>
      <div className="page-subtitle">Search the Goodreads 10k dataset</div>

      {/* Search */}
      <div style={{ position: 'relative', marginBottom: '1.5rem', maxWidth: 480 }}>
        <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
        <input
          type="text"
          placeholder="Search by title or author..."
          value={query}
          onChange={onSearch}
          style={{
            width: '100%',
            padding: '0.6rem 0.75rem 0.6rem 2.25rem',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            fontSize: '0.9rem',
            fontFamily: 'var(--font-body)',
            outline: 'none',
            background: 'white',
          }}
        />
      </div>

      {loading && <div className="loading">Searching...</div>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        {books.map(book => (
          <BookCard key={book.id} book={book} />
        ))}
        {!loading && books.length === 0 && (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted)' }}>
            No books found for "{query}"
          </div>
        )}
      </div>
    </div>
  )
}
