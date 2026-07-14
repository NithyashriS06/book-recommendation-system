import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import RecommendationsPage from './pages/RecommendationsPage'
import UsersPage from './pages/UsersPage'
import BooksPage from './pages/BooksPage'
import MetricsPage from './pages/MetricsPage'

export default function App() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main style={{ flex: 1, overflow: 'auto' }}>
        <Routes>
          <Route path="/"        element={<RecommendationsPage />} />
          <Route path="/users"   element={<UsersPage />} />
          <Route path="/books"   element={<BooksPage />} />
          <Route path="/metrics" element={<MetricsPage />} />
        </Routes>
      </main>
    </div>
  )
}
