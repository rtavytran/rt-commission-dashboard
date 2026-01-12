# OAuth2 PKCE Implementation Guide

Complete guide to implementing OAuth2 Authorization Code flow with PKCE for rtwork app dashboard authentication.

---

## Overview

**Goal**: Allow users to view dashboard without separate login, leveraging existing Keycloak authentication.

**Flow**: User already logged into rtwork → Opens dashboard → Quick redirect to Keycloak → Keycloak sees active session → Auto-approves → Redirects back with code → Exchange for token → Dashboard loads

**User sees**: Brief loading screen (< 1 second), no login form

---

## Prerequisites

### 1. Create OAuth2 Client in Keycloak

Navigate to Keycloak Admin Console:
- **Realm**: `rta`
- **Clients** → **Create Client**

**Settings**:
```yaml
Client ID: dashboard-viewer
Client Protocol: openid-connect
Access Type: public
Standard Flow Enabled: ON
Direct Access Grants Enabled: OFF
Service Accounts Enabled: OFF

Valid Redirect URIs:
  - https://your-dashboard-domain.com/callback
  - https://your-dashboard-domain.com/*  # For testing

Web Origins:
  - https://your-dashboard-domain.com

PKCE Code Challenge Method: S256  # Required for security
```

### 2. Test Keycloak Endpoints

Verify endpoints are accessible:

```bash
# Discovery endpoint (lists all OAuth2 endpoints)
curl https://accounts.rtworkspace.com/auth/realms/rta/.well-known/openid-configuration

# Response should include:
# - authorization_endpoint
# - token_endpoint
# - jwks_uri
```

---

## Implementation

### Step 1: Create OAuth2 Helper Library

Create `oauth2-helper.js`:

```javascript
/**
 * OAuth2 PKCE Helper for Keycloak Authentication
 */

const KEYCLOAK_CONFIG = {
  issuer: 'https://accounts.rtworkspace.com/auth/realms/rta',
  authorizationEndpoint: 'https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/auth',
  tokenEndpoint: 'https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/token',
  clientId: 'dashboard-viewer',
  redirectUri: window.location.origin + '/callback',
  scope: 'openid profile email'
}

class OAuth2Client {
  constructor(config) {
    this.config = config
  }

  /**
   * Generate random string for code verifier
   */
  generateRandomString(length) {
    const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
    const randomValues = new Uint8Array(length)
    crypto.getRandomValues(randomValues)
    return Array.from(randomValues)
      .map(v => charset[v % charset.length])
      .join('')
  }

  /**
   * Generate SHA256 hash (for PKCE challenge)
   */
  async sha256(plain) {
    const encoder = new TextEncoder()
    const data = encoder.encode(plain)
    const hash = await crypto.subtle.digest('SHA-256', data)
    return hash
  }

  /**
   * Base64 URL encode
   */
  base64urlencode(buffer) {
    const bytes = new Uint8Array(buffer)
    const binary = String.fromCharCode(...bytes)
    const base64 = btoa(binary)
    return base64
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '')
  }

  /**
   * Generate PKCE code verifier and challenge
   */
  async generatePKCE() {
    const codeVerifier = this.generateRandomString(128)
    const hashed = await this.sha256(codeVerifier)
    const codeChallenge = this.base64urlencode(hashed)

    return {
      codeVerifier,
      codeChallenge,
      codeChallengeMethod: 'S256'
    }
  }

  /**
   * Start OAuth2 authorization flow
   * Redirects to Keycloak login page
   */
  async authorize() {
    // Generate PKCE parameters
    const pkce = await this.generatePKCE()

    // Store code verifier for later use (after redirect back)
    sessionStorage.setItem('oauth2_code_verifier', pkce.codeVerifier)

    // Build authorization URL
    const params = new URLSearchParams({
      client_id: this.config.clientId,
      redirect_uri: this.config.redirectUri,
      response_type: 'code',
      scope: this.config.scope,
      code_challenge: pkce.codeChallenge,
      code_challenge_method: pkce.codeChallengeMethod,
      // Optional: state parameter for CSRF protection
      state: this.generateRandomString(32)
    })

    // Store state for verification after redirect
    sessionStorage.setItem('oauth2_state', params.get('state'))

    // Redirect to Keycloak
    const authUrl = `${this.config.authorizationEndpoint}?${params.toString()}`
    window.location.href = authUrl
  }

  /**
   * Handle OAuth2 callback
   * Exchanges authorization code for access token
   */
  async handleCallback() {
    // Parse URL parameters
    const urlParams = new URLSearchParams(window.location.search)
    const code = urlParams.get('code')
    const state = urlParams.get('state')
    const error = urlParams.get('error')

    // Check for errors
    if (error) {
      throw new Error(`OAuth2 error: ${error} - ${urlParams.get('error_description')}`)
    }

    if (!code) {
      throw new Error('No authorization code received')
    }

    // Verify state (CSRF protection)
    const storedState = sessionStorage.getItem('oauth2_state')
    if (state !== storedState) {
      throw new Error('State mismatch - possible CSRF attack')
    }

    // Get code verifier from storage
    const codeVerifier = sessionStorage.getItem('oauth2_code_verifier')
    if (!codeVerifier) {
      throw new Error('Code verifier not found - session expired?')
    }

    // Exchange code for tokens
    const tokens = await this.exchangeCodeForTokens(code, codeVerifier)

    // Clean up session storage
    sessionStorage.removeItem('oauth2_code_verifier')
    sessionStorage.removeItem('oauth2_state')

    return tokens
  }

  /**
   * Exchange authorization code for tokens
   */
  async exchangeCodeForTokens(code, codeVerifier) {
    const response = await fetch(this.config.tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: this.config.redirectUri,
        client_id: this.config.clientId,
        code_verifier: codeVerifier
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(`Token exchange failed: ${error.error_description || error.error}`)
    }

    const tokens = await response.json()

    // tokens = {
    //   access_token: "eyJhbGc...",
    //   refresh_token: "eyJhbGc...",
    //   id_token: "eyJhbGc...",
    //   token_type: "Bearer",
    //   expires_in: 3600
    // }

    return tokens
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshAccessToken(refreshToken) {
    const response = await fetch(this.config.tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: this.config.clientId
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(`Token refresh failed: ${error.error_description || error.error}`)
    }

    return await response.json()
  }

  /**
   * Decode JWT (without verification - for display only!)
   */
  decodeJWT(token) {
    const parts = token.split('.')
    if (parts.length !== 3) {
      throw new Error('Invalid JWT format')
    }

    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  }

  /**
   * Check if token is expired
   */
  isTokenExpired(token) {
    try {
      const decoded = this.decodeJWT(token)
      const now = Math.floor(Date.now() / 1000)
      return decoded.exp < now
    } catch (e) {
      return true
    }
  }
}

// Export singleton instance
export const oauth2Client = new OAuth2Client(KEYCLOAK_CONFIG)
```

### Step 2: Create Token Storage Manager

Create `token-storage.js`:

```javascript
/**
 * Token Storage Manager
 * Handles storing/retrieving tokens with fallback strategies
 */

class TokenStorage {
  constructor() {
    this.storageKey = 'dashboard_tokens'
    this.storageAvailable = this.checkStorageAvailability()
  }

  /**
   * Check if localStorage is available and persists
   */
  checkStorageAvailability() {
    try {
      const testKey = '__storage_test__'
      localStorage.setItem(testKey, 'test')
      const value = localStorage.getItem(testKey)
      localStorage.removeItem(testKey)
      return value === 'test'
    } catch (e) {
      console.warn('localStorage not available:', e)
      return false
    }
  }

  /**
   * Save tokens
   */
  saveTokens(tokens) {
    if (!this.storageAvailable) {
      console.warn('Storage not available - tokens will be lost on page reload')
      // Store in memory only (for current session)
      this._memoryTokens = tokens
      return
    }

    try {
      const data = {
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        expires_at: Math.floor(Date.now() / 1000) + tokens.expires_in,
        stored_at: new Date().toISOString()
      }
      localStorage.setItem(this.storageKey, JSON.stringify(data))
    } catch (e) {
      console.error('Failed to save tokens:', e)
      this._memoryTokens = tokens
    }
  }

  /**
   * Get tokens
   */
  getTokens() {
    // Check memory first (for non-persistent storage)
    if (this._memoryTokens) {
      return this._memoryTokens
    }

    if (!this.storageAvailable) {
      return null
    }

    try {
      const data = localStorage.getItem(this.storageKey)
      if (!data) return null

      return JSON.parse(data)
    } catch (e) {
      console.error('Failed to retrieve tokens:', e)
      return null
    }
  }

  /**
   * Clear tokens
   */
  clearTokens() {
    this._memoryTokens = null

    if (this.storageAvailable) {
      try {
        localStorage.removeItem(this.storageKey)
      } catch (e) {
        console.error('Failed to clear tokens:', e)
      }
    }
  }

  /**
   * Check if we have valid tokens
   */
  hasValidTokens() {
    const tokens = this.getTokens()
    if (!tokens || !tokens.access_token) {
      return false
    }

    // Check expiration
    const now = Math.floor(Date.now() / 1000)
    return tokens.expires_at > now
  }
}

export const tokenStorage = new TokenStorage()
```

### Step 3: Create Dashboard Login Page

Create `dashboard-login.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loading Dashboard...</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        .loading-container {
            text-align: center;
            color: white;
        }

        .spinner {
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error {
            background: white;
            color: #721c24;
            padding: 20px;
            border-radius: 10px;
            max-width: 400px;
        }
    </style>
</head>
<body>
    <div class="loading-container">
        <div class="spinner"></div>
        <p id="status">Checking authentication...</p>
    </div>

    <script type="module">
        import { oauth2Client } from './oauth2-helper.js'
        import { tokenStorage } from './token-storage.js'

        async function init() {
            const status = document.getElementById('status')

            try {
                // Are we coming back from OAuth2 redirect?
                if (window.location.pathname === '/callback' || window.location.search.includes('code=')) {
                    status.textContent = 'Processing authentication...'

                    // Exchange code for tokens
                    const tokens = await oauth2Client.handleCallback()

                    // Save tokens
                    tokenStorage.saveTokens(tokens)

                    // Redirect to dashboard
                    window.location.href = '/dashboard.html'
                    return
                }

                // Check if we already have valid tokens
                if (tokenStorage.hasValidTokens()) {
                    status.textContent = 'Authentication valid, loading dashboard...'
                    window.location.href = '/dashboard.html'
                    return
                }

                // Check if we have refresh token
                const tokens = tokenStorage.getTokens()
                if (tokens && tokens.refresh_token) {
                    status.textContent = 'Refreshing session...'

                    try {
                        const newTokens = await oauth2Client.refreshAccessToken(tokens.refresh_token)
                        tokenStorage.saveTokens(newTokens)
                        window.location.href = '/dashboard.html'
                        return
                    } catch (e) {
                        console.warn('Token refresh failed:', e)
                        // Fall through to re-authenticate
                    }
                }

                // No valid tokens - start OAuth2 flow
                status.textContent = 'Redirecting to login...'
                await oauth2Client.authorize()

            } catch (error) {
                console.error('Authentication error:', error)
                document.querySelector('.loading-container').innerHTML = `
                    <div class="error">
                        <h2>Authentication Error</h2>
                        <p>${error.message}</p>
                        <button onclick="location.reload()">Try Again</button>
                    </div>
                `
            }
        }

        init()
    </script>
</body>
</html>
```

### Step 4: Update Dashboard Page

Update `dashboard.html`:

```javascript
// At the top of dashboard.html <script> section
import { oauth2Client } from './oauth2-helper.js'
import { tokenStorage } from './token-storage.js'

const EDGE_FUNCTION_URL = 'https://pphoiqknkmwzstuokdmz.supabase.co/functions/v1/dashboard-stats'

async function init() {
    // Check authentication
    if (!tokenStorage.hasValidTokens()) {
        // Not authenticated - redirect to login
        window.location.href = '/dashboard-login.html'
        return
    }

    // Get access token
    const tokens = tokenStorage.getTokens()
    const accessToken = tokens.access_token

    // Load dashboard data
    try {
        await loadDashboard(accessToken)
    } catch (error) {
        if (error.status === 401) {
            // Token invalid - try refresh
            if (tokens.refresh_token) {
                try {
                    const newTokens = await oauth2Client.refreshAccessToken(tokens.refresh_token)
                    tokenStorage.saveTokens(newTokens)
                    await loadDashboard(newTokens.access_token)
                    return
                } catch (refreshError) {
                    console.error('Token refresh failed:', refreshError)
                }
            }

            // Refresh failed - re-authenticate
            tokenStorage.clearTokens()
            window.location.href = '/dashboard-login.html'
        } else {
            throw error
        }
    }
}

async function loadDashboard(accessToken) {
    const response = await fetch(EDGE_FUNCTION_URL, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        },
        body: '{}'
    })

    if (!response.ok) {
        const error = new Error(`HTTP ${response.status}`)
        error.status = response.status
        throw error
    }

    const data = await response.json()

    // Render dashboard
    renderDashboard(data)
}

function renderDashboard(data) {
    // Your existing dashboard rendering code
    document.getElementById('user-name').textContent = data.user.full_name
    // ... etc
}

// Add logout function
function logout() {
    tokenStorage.clearTokens()
    window.location.href = '/dashboard-login.html'
}

// Initialize
init()
```

---

## Testing

### Test Locally

```bash
# Start local web server
python3 -m http.server 8000

# Open in browser
open http://localhost:8000/dashboard-login.html

# Expected flow:
# 1. Shows "Checking authentication..."
# 2. Redirects to Keycloak (https://accounts.rtworkspace.com/...)
# 3. If already logged into rtwork → Instant redirect back
# 4. If not logged in → Shows Keycloak login form
# 5. After login → Redirects back to /callback?code=...
# 6. Exchanges code for tokens
# 7. Loads dashboard.html
```

### Test in rtwork Mobile App

```javascript
// In rtwork app, load dashboard via webview
App.openWebView('https://your-dashboard-domain.com/dashboard-login.html')

// Expected:
// - Quick redirect to Keycloak
// - Instant redirect back (user already logged in)
// - Dashboard loads
// Total time: < 1 second
```

---

## Troubleshooting

### Error: "Invalid redirect_uri"

**Cause**: Redirect URI not whitelisted in Keycloak client

**Solution**: Add your redirect URI to Keycloak client settings

### Error: "PKCE validation failed"

**Cause**: Code verifier not found or incorrect

**Solution**: Ensure code_verifier is stored in sessionStorage before redirect

### Issue: Redirect loop

**Cause**: Token storage failing, keeps re-authenticating

**Solution**: Check browser console for storage errors, verify localStorage works

### Issue: "Token expired" immediately

**Cause**: Server time mismatch or token already used

**Solution**:
- Check server time is accurate
- Don't reuse authorization codes (single-use only)

---

## Production Deployment

### 1. Use HTTPS

```
❌ http://dashboard.example.com
✅ https://dashboard.example.com
```

OAuth2 requires HTTPS in production.

### 2. Configure CORS

In Edge Function, allow your domain:

```typescript
headers: {
  'Access-Control-Allow-Origin': 'https://your-dashboard-domain.com',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Authorization, Content-Type'
}
```

### 3. Set Proper Redirect URI

Update `KEYCLOAK_CONFIG.redirectUri` to production URL:

```javascript
redirectUri: 'https://your-dashboard-domain.com/callback'
```

### 4. Monitor Token Usage

```javascript
// Log token usage for debugging
console.log('Token issued at:', new Date(tokens.iat * 1000))
console.log('Token expires at:', new Date(tokens.exp * 1000))
console.log('Time until expiry:', (tokens.exp - Date.now()/1000) + ' seconds')
```

---

## Security Checklist

- [ ] PKCE enabled (S256 code challenge method)
- [ ] State parameter validated (CSRF protection)
- [ ] HTTPS used in production
- [ ] Tokens stored securely (localStorage with short expiration)
- [ ] Edge Function validates JWT signature
- [ ] Refresh tokens used for long-lived sessions
- [ ] Logout clears all tokens
- [ ] No sensitive data in URL parameters

---

## Next Steps

1. Create OAuth2 client in Keycloak
2. Test storage persistence in mobile webview
3. Implement OAuth2 helper library
4. Update dashboard to use OAuth2 flow
5. Test thoroughly
6. Deploy to production
7. Monitor for issues

---

**Document Version**: 1.0
**Last Updated**: 2026-01-12
**Status**: Ready for Implementation
