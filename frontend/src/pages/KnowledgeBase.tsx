// Stub pages — quick implementations
import { Link } from 'react-router-dom'

export default function KnowledgeBase() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">🧠 Knowledge Base</h1>
        <p className="page-subtitle">Organize documents into searchable collections</p>
      </div>
      <div className="alert alert-info mb-4">
        <span>💡</span>
        <span>Knowledge Base uses the same RAG pipeline as the <Link to="/documents">Documents</Link> page. Upload and index your documents there, then query them here by collection.</span>
      </div>
      <div className="grid-3">
        {['My Research', 'College Notes', 'Projects', 'Technical Docs', 'Meeting Notes', 'Personal'].map(col => (
          <div key={col} className="card" style={{ cursor: 'pointer', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: 12 }}>📚</div>
            <div style={{ fontWeight: 600 }}>{col}</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>0 documents</div>
            <div className="flex gap-2 mt-3" style={{ justifyContent: 'center' }}>
              <Link to="/documents" className="btn btn-secondary btn-sm">+ Add Docs</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
