import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
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

function App() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [twoFactorCode, setTwoFactorCode] = useState('')
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '')
  const [activeUser, setActiveUser] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const [engagementUsername, setEngagementUsername] = useState('')
  const [followersUsername, setFollowersUsername] = useState('')
  const [followersFormat, setFollowersFormat] = useState('txt')
  const [postUrl, setPostUrl] = useState('')
  const [profileUsername, setProfileUsername] = useState('')

  const [engagementResult, setEngagementResult] = useState(null)
  const [followersResult, setFollowersResult] = useState(null)
  const [postResult, setPostResult] = useState(null)
  const [profileResult, setProfileResult] = useState(null)

  const isAuthenticated = Boolean(token)
  const exportFileUrl = useMemo(() => {
    if (!followersResult?.file_url) return ''
    return toAbsoluteApiUrl(followersResult.file_url)
  }, [followersResult])

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

  useEffect(() => {
    if (!activeUser) return
    setEngagementUsername((value) => value || activeUser)
    setFollowersUsername((value) => value || activeUser)
    setProfileUsername((value) => value || activeUser)
  }, [activeUser])

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
        two_factor_code: twoFactorCode || null,
      }
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: payload,
      })

      localStorage.setItem(TOKEN_KEY, data.access_token)
      setToken(data.access_token)
      setPassword('')
      setTwoFactorCode('')
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

  const submitEngagement = async (event) => {
    event.preventDefault()
    const targetUsername = (engagementUsername || activeUser).trim()
    if (!targetUsername) {
      setError('Enter a profile username for engagement.')
      return
    }

    await runProtectedAction('engagement', async () => {
      const data = await apiRequest('/engagement/calculate', {
        method: 'POST',
        token,
        body: { username: targetUsername },
      })
      setEngagementResult(data)
      setNotice('Engagement score generated.')
    })
  }

  const submitFollowers = async (event) => {
    event.preventDefault()
    const targetUsername = (followersUsername || activeUser).trim()
    if (!targetUsername) {
      setError('Enter a profile username for followers export.')
      return
    }

    await runProtectedAction('followers', async () => {
      const data = await apiRequest('/followers/export', {
        method: 'POST',
        token,
        body: {
          username: targetUsername,
          output_format: followersFormat,
        },
      })
      setFollowersResult(data)
      setNotice('Followers export generated.')
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
      setNotice('Post download started and saved on backend.')
    })
  }

  const submitProfilePicture = async (event) => {
    event.preventDefault()
    const targetUsername = (profileUsername || activeUser).trim()
    if (!targetUsername) {
      setError('Enter a profile username for profile picture download.')
      return
    }

    await runProtectedAction('profile', async () => {
      const data = await apiRequest('/profile/picture', {
        method: 'POST',
        token,
        body: { username: targetUsername },
      })
      setProfileResult(data)
      setNotice('Profile picture download completed.')
    })
  }

  return (
    <main className="app-shell">
      <div className="app-bg app-bg-a"></div>
      <div className="app-bg app-bg-b"></div>

      <header className="hero">
        <p className="eyebrow">Instagram Automation Dashboard</p>
        <h1>Insta Ops Console</h1>
        <p className="subtitle">Login once and run engagement checks, exports, and download tasks from one clean dashboard.</p>
      </header>

      <section className="panel auth-panel">
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
            <input value={twoFactorCode} onChange={(event) => setTwoFactorCode(event.target.value)} placeholder="123456" />
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
        <article className="panel">
          <h2>Engagement Score</h2>
          <form className="grid-form" onSubmit={submitEngagement}>
            <label>
              Profile Username
              <input value={engagementUsername} onChange={(event) => setEngagementUsername(event.target.value)} required placeholder="target profile" />
            </label>
            <button type="submit" disabled={!isAuthenticated || busyAction === 'engagement'}>
              {busyAction === 'engagement' ? 'Calculating...' : 'Calculate'}
            </button>
          </form>

          {engagementResult && (
            <div className="result-box">
              <p>
                <strong>User:</strong> {engagementResult.username}
              </p>
              <p>
                <strong>Followers:</strong> {engagementResult.followers}
              </p>
              <p>
                <strong>Posts:</strong> {engagementResult.total_posts}
              </p>
              <p>
                <strong>Total Likes:</strong> {engagementResult.total_likes}
              </p>
              <p>
                <strong>Total Comments:</strong> {engagementResult.total_comments}
              </p>
              <p>
                <strong>Rate:</strong> {engagementResult.engagement_rate}%
              </p>
            </div>
          )}
        </article>

        <article className="panel">
          <h2>Followers Export</h2>
          <form className="grid-form" onSubmit={submitFollowers}>
            <label>
              Profile Username
              <input value={followersUsername} onChange={(event) => setFollowersUsername(event.target.value)} required placeholder="target profile" />
            </label>
            <label>
              Export Format
              <select value={followersFormat} onChange={(event) => setFollowersFormat(event.target.value)}>
                <option value="txt">TXT</option>
                <option value="json">JSON</option>
              </select>
            </label>
            <button type="submit" disabled={!isAuthenticated || busyAction === 'followers'}>
              {busyAction === 'followers' ? 'Exporting...' : 'Export Followers'}
            </button>
          </form>

          {followersResult && (
            <div className="result-box">
              <p>
                <strong>User:</strong> {followersResult.username}
              </p>
              <p>
                <strong>Count:</strong> {followersResult.count}
              </p>
              <p>
                <strong>File:</strong> {followersResult.file_name}
              </p>
              {exportFileUrl && (
                <a href={exportFileUrl} target="_blank" rel="noreferrer" className="download-link">
                  Download Export File
                </a>
              )}
            </div>
          )}
        </article>

        <article className="panel">
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
                <strong>Owner:</strong> {postResult.owner_username}
              </p>
              <p>
                <strong>Saved To:</strong> {postResult.output_folder}
              </p>
            </div>
          )}
        </article>

        <article className="panel">
          <h2>Profile Picture</h2>
          <form className="grid-form" onSubmit={submitProfilePicture}>
            <label>
              Profile Username
              <input value={profileUsername} onChange={(event) => setProfileUsername(event.target.value)} required placeholder="target profile" />
            </label>
            <button type="submit" disabled={!isAuthenticated || busyAction === 'profile'}>
              {busyAction === 'profile' ? 'Downloading...' : 'Download Picture'}
            </button>
          </form>

          {profileResult && (
            <div className="result-box">
              <p>
                <strong>User:</strong> {profileResult.username}
              </p>
              <p>
                <strong>Saved To:</strong> {profileResult.output_folder}
              </p>
            </div>
          )}
        </article>
      </section>

    </main>
  )
}

export default App
