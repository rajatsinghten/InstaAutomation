import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const TOKEN_KEY = 'instaloader_api_token'

function getErrorMessage(data, fallback = 'Request failed') {
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (data.code && data.message) return `${data.code}: ${data.message}`
  if (data.error_code && data.message) return `${data.error_code}: ${data.message}`
  if (data.message) return data.message
  if (Array.isArray(data.detail)) {
    return data.detail.map((item) => item.msg || JSON.stringify(item)).join(', ')
  }
  if (data.detail && typeof data.detail === 'string') return data.detail
  return fallback
}

function toAbsoluteApiUrl(pathOrUrl) {
  if (!pathOrUrl) return ''

  try {
    return new URL(pathOrUrl).toString()
  } catch {
    const apiRoot = new URL(API_BASE_URL)
    const cleanPath = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`
    return `${apiRoot.origin}${cleanPath}`
  }
}

async function apiRequest(path, { method = 'GET', token, body } = {}) {
  const headers = {
    'Content-Type': 'application/json',
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    throw new Error(getErrorMessage(payload, `HTTP ${response.status}`))
  }

  return payload
}

function formatDate(value) {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString()
}

function pickFollowerArray(payload) {
  if (Array.isArray(payload.followers)) return payload.followers
  if (Array.isArray(payload.unfollowers)) return payload.unfollowers
  if (Array.isArray(payload.not_following_back)) return payload.not_following_back
  if (Array.isArray(payload.mutual_followers)) return payload.mutual_followers
  return []
}

function App() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '')
  const [activeUser, setActiveUser] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const [refreshData, setRefreshData] = useState(false)
  const [postUrl, setPostUrl] = useState('')

  const [followersResult, setFollowersResult] = useState(null)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [postResult, setPostResult] = useState(null)

  const isAuthenticated = Boolean(token)
  const mediaUrl = useMemo(() => toAbsoluteApiUrl(postResult?.media_url || ''), [postResult])
  const sourceMediaUrl = useMemo(() => toAbsoluteApiUrl(postResult?.source_media_url || ''), [postResult])
  const summaryCards = useMemo(() => {
    if (!analysisResult) return []
    return [
      { label: 'Followers', value: analysisResult.total_followers },
      { label: 'Following', value: analysisResult.total_following },
      { label: 'Unfollowers', value: analysisResult.unfollowers },
      { label: 'Not Following Back', value: analysisResult.not_following_back },
      { label: 'Mutual', value: analysisResult.mutual_followers },
      { label: 'Rate', value: `${analysisResult.engagement_rate}%` },
    ]
  }, [analysisResult])

  useEffect(() => {
    if (!token) {
      setActiveUser('')
      return
    }

    let ignore = false

    const validateToken = async () => {
      try {
        const status = await apiRequest('/auth/status', { token })
        if (!ignore) {
          setActiveUser(status.username || '')
          setError('')
        }
      } catch {
        if (!ignore) {
          localStorage.removeItem(TOKEN_KEY)
          setToken('')
          setActiveUser('')
          setNotice('Session expired. Please login again.')
        }
      }
    }

    validateToken()

    return () => {
      ignore = true
    }
  }, [token])

  const clearMessages = () => {
    setNotice('')
    setError('')
  }

  const handleLogin = async (event) => {
    event.preventDefault()
    clearMessages()
    setBusyAction('login')

    try {
      const payload = {
        username,
        password,
        otp_code: otpCode || null,
      }
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: payload,
      })

      localStorage.setItem(TOKEN_KEY, data.access_token)
      setToken(data.access_token)
      setPassword('')
      setOtpCode('')
      setNotice('Login successful. You can now run Instagram actions.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusyAction('')
    }
  }

  const handleLogout = async () => {
    clearMessages()
    setBusyAction('logout')

    try {
      await apiRequest('/auth/logout', {
        method: 'POST',
        token,
      })
    } catch {
      // Clear local auth even if backend already invalidated the session.
    } finally {
      localStorage.removeItem(TOKEN_KEY)
      setToken('')
      setActiveUser('')
      setFollowersResult(null)
      setAnalysisResult(null)
      setPostResult(null)
      setBusyAction('')
      setNotice('Logged out successfully.')
    }
  }

  const runProtectedAction = async (actionName, fn) => {
    clearMessages()
    setBusyAction(actionName)
    try {
      await fn()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusyAction('')
    }
  }

  const querySuffix = refreshData ? '?refresh=true' : ''

  const loadFollowerSet = async (key, path, title) => {
    await runProtectedAction(key, async () => {
      const payload = await apiRequest(`${path}${querySuffix}`, { token })
      const users = pickFollowerArray(payload)
      setFollowersResult({
        title,
        users,
        total_count: payload.total_count ?? users.length,
        fetched_at: payload.fetched_at,
      })
      setNotice(`${title} loaded successfully.`)
    })
  }

  const loadAnalysisSummary = async () => {
    await runProtectedAction('summary', async () => {
      const payload = await apiRequest(`/analysis/summary${querySuffix}`, { token })
      setAnalysisResult(payload)
      setNotice('Analysis summary updated.')
    })
  }

  const submitPostDownload = async (event) => {
    event.preventDefault()
    const normalizedUrl = postUrl.trim()
    if (!normalizedUrl) {
      setError('Enter a post or reel URL.')
      return
    }

    await runProtectedAction('post', async () => {
      const data = await apiRequest('/posts/download', {
        method: 'POST',
        token,
        body: { url: normalizedUrl },
      })
      setPostResult(data)
      setNotice('Media downloaded successfully.')
    })
  }

  const previewUsers = followersResult?.users?.slice(0, 12) || []

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Instagram Automation Dashboard</p>
        <h1>Insta Ops Console</h1>
        <p className="subtitle">Login once and run follower analysis and post download tasks from one clean dashboard.</p>
        <div className="hero-meta">
          <span className={`hero-chip ${isAuthenticated ? 'success' : ''}`}>
            {isAuthenticated ? 'Session Active' : 'Session Inactive'}
          </span>
          {activeUser && <span className="hero-chip">User: {activeUser}</span>}
        </div>
      </header>

      <section className="panel auth-panel panel-auth">
        <div className="panel-head">
          <h2>Authentication</h2>
          {isAuthenticated ? <span className="chip success">Connected</span> : <span className="chip">Not Logged In</span>}
        </div>

        <form className="grid-form" onSubmit={handleLogin}>
          <label>
            Username
            <input value={username} onChange={(event) => setUsername(event.target.value)} required placeholder="instagram username" />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required placeholder="instagram password" />
          </label>
          <label>
            2FA Code (optional)
            <input value={otpCode} onChange={(event) => setOtpCode(event.target.value)} placeholder="123456" />
          </label>
          <div className="actions-row">
            <button type="submit" disabled={busyAction === 'login'}>
              {busyAction === 'login' ? 'Logging in...' : 'Login'}
            </button>
            <button type="button" className="ghost" disabled={!isAuthenticated || busyAction === 'logout'} onClick={handleLogout}>
              {busyAction === 'logout' ? 'Logging out...' : 'Logout'}
            </button>
          </div>
        </form>

        {activeUser && (
          <p className="meta">
            Active session: <strong>{activeUser}</strong>
          </p>
        )}
      </section>

      {(notice || error) && (
        <section className="alerts">
          {notice && <div className="notice">{notice}</div>}
          {error && <div className="error">{error}</div>}
        </section>
      )}

      <section className="tool-grid">
        <article className="panel panel-followers">
          <h2>Follower Analysis</h2>
          <div className="grid-form">
            <label className="inline-check">
              <input type="checkbox" checked={refreshData} onChange={(event) => setRefreshData(event.target.checked)} />
              Force refresh (ignore cache)
            </label>
            <div className="actions-row wrap">
              <button type="button" onClick={() => loadFollowerSet('followers-list', '/followers/list', 'Followers')} disabled={!isAuthenticated || busyAction === 'followers-list'}>
                {busyAction === 'followers-list' ? 'Loading...' : 'Followers'}
              </button>
              <button type="button" onClick={() => loadFollowerSet('unfollowers', '/followers/unfollowers', 'Unfollowers')} disabled={!isAuthenticated || busyAction === 'unfollowers'}>
                {busyAction === 'unfollowers' ? 'Loading...' : 'Unfollowers'}
              </button>
              <button type="button" onClick={() => loadFollowerSet('not-following', '/followers/not-following', 'Not Following Back')} disabled={!isAuthenticated || busyAction === 'not-following'}>
                {busyAction === 'not-following' ? 'Loading...' : 'Not Following Back'}
              </button>
              <button type="button" onClick={() => loadFollowerSet('mutual', '/followers/mutual', 'Mutual Followers')} disabled={!isAuthenticated || busyAction === 'mutual'}>
                {busyAction === 'mutual' ? 'Loading...' : 'Mutual'}
              </button>
            </div>
          </div>

          {followersResult && (
            <div className="result-box">
              <p>
                <strong>Type:</strong> {followersResult.title}
              </p>
              <p>
                <strong>Total:</strong> {followersResult.total_count}
              </p>
              <p>
                <strong>Fetched At:</strong> {formatDate(followersResult.fetched_at)}
              </p>
              <div className="result-list">
                <strong>Preview:</strong>
                {previewUsers.length === 0 ? (
                  <p>No users found for this category.</p>
                ) : (
                  <ul>
                    {previewUsers.map((user) => (
                      <li key={user.username}>{user.username}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </article>

        <article className="panel panel-summary">
          <h2>Summary Stats</h2>
          <div className="grid-form">
            <button type="button" disabled={!isAuthenticated || busyAction === 'summary'} onClick={loadAnalysisSummary}>
              {busyAction === 'summary' ? 'Loading...' : 'Load Summary'}
            </button>
          </div>

          {analysisResult && (
            <div className="result-box">
              <div className="stats-grid cards">
                {summaryCards.map((item) => (
                  <div className="stat-card" key={item.label}>
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>
              <p>
                <strong>Fetched At:</strong> {formatDate(analysisResult.fetched_at)}
              </p>
            </div>
          )}
        </article>

        <article className="panel panel-download">
          <h2>Post / Reel Download</h2>
          <form className="grid-form" onSubmit={submitPostDownload}>
            <label>
              Post or Reel URL
              <input value={postUrl} onChange={(event) => setPostUrl(event.target.value)} required placeholder="https://www.instagram.com/p/..." />
            </label>
            <button type="submit" disabled={!isAuthenticated || busyAction === 'post'}>
              {busyAction === 'post' ? 'Downloading...' : 'Download'}
            </button>
          </form>

          {postResult && (
            <div className="result-box">
              <p>
                <strong>Shortcode:</strong> {postResult.shortcode}
              </p>
              <p>
                <strong>Media Type:</strong> {postResult.media_type}
              </p>
              <p>
                <strong>Downloaded At:</strong> {formatDate(postResult.downloaded_at)}
              </p>
              {postResult.caption && (
                <p>
                  <strong>Caption:</strong> {postResult.caption}
                </p>
              )}
              {mediaUrl && (
                <a href={mediaUrl} target="_blank" rel="noreferrer" className="download-link">
                  Download Media File
                </a>
              )}
              {sourceMediaUrl && sourceMediaUrl !== mediaUrl && (
                <a href={sourceMediaUrl} target="_blank" rel="noreferrer" className="download-link secondary-link">
                  Open Source Media URL
                </a>
              )}
            </div>
          )}
        </article>
      </section>

    </main>
  )
}

export default App
