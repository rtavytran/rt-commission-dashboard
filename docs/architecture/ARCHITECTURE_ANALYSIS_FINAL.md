# RT Commission Dashboard - Complete Architecture Analysis

**Date**: 2026-01-12
**Version**: 3.0 (Final with OAuth2 Analysis)
**Purpose**: Comprehensive evaluation of all architectural approaches for secure multi-platform data access
**Primary Concern**: Data security while maintaining excellent user experience

---

## Executive Summary

### Critical Updates (2026-01-12)

**❌ Blocker Discovered**: rtwork app developer **will not whitelist** our endpoint for `App.callApi` with `includeToken=true` (JWT auto-attachment).

**🔄 Developer Suggestion**: Use OAuth2 instead.

**🎯 New Requirement**: Find authentication solution that:
1. Works without rtwork's `App.callApi` JWT whitelist
2. Provides good user experience (minimal login friction)
3. Maintains security standards
4. Handles mobile webview storage limitations

**New Restrictions (2026-01-12)**:
- No Keycloak client changes (cannot add OAuth2/PKCE client or register redirect URIs).
- No bridge changes (cannot add allowlist entries for supabase.co; cannot add get/set token functions).
- Dashboard is delivered as static HTML/CSS (no hosted “dashboard URL” to register).

---

## Platform Understanding

### rtwork Platform Architecture

| Feature | Native Mobile | Web Browser | Notes |
|---------|--------------|-------------|-------|
| **Codebase** | Same HTML/JS/CSS | Same HTML/JS/CSS | ✅ Truly hybrid |
| **`App.callApi`** | Native bridge | Web polyfill | ✅ Works everywhere |
| **`includeToken=true`** | Keycloak JWT attached | Keycloak JWT attached | ❌ **Requires whitelist** |
| **Keycloak Session** | User logged in | User logged in | ✅ SSO available |
| **localStorage** | ⚠️ May not persist | ✅ Persists | ⚠️ Platform-dependent |
| **Cookies** | ❓ Unknown | ✅ Supported | Need to verify |
| **Native Bridge** | ✅ Available | ❌ Not available | Platform-specific |

### Key Constraints

1. **Cannot use `App.callApi(includeToken=true)`** for our endpoint (whitelist rejected)
2. **localStorage may not persist** in mobile webview (closes = loses state)
3. **Users already authenticated** via Keycloak in rtwork app (good UX = no re-login)
4. **Hybrid app** = solution must work on both mobile native and web browser

---

## Authentication Solutions Comparison

### Option 1: Keycloak JWT via App.callApi (ORIGINAL PLAN - NOW BLOCKED)

**Status**: ❌ **BLOCKED** - rtwork developer won't whitelist endpoint

```
rtwork app → App.callApi(includeToken=true) →
Keycloak JWT auto-attached → Edge Function validates JWT → Returns data
```

**Why it was good**:
- ✅ True SSO (no separate login)
- ✅ Secure (JWT validation)
- ✅ Seamless UX

**Why it doesn't work**:
- ❌ Requires rtwork developer to whitelist our endpoint
- ❌ Developer rejected this request

**Verdict**: Not viable 🚫

---

### Option 2: OAuth2 Authorization Code + PKCE (RECOMMENDED)

**Status**: ✅ **VIABLE** - Standard OAuth2 flow

**Current viability**: Blocked under current constraints (cannot create a Keycloak public client or register redirect URIs). Requires Keycloak admin cooperation to implement.

```
User opens dashboard → Check if token exists →
NO → Redirect to Keycloak OAuth2 login →
Keycloak sees user already logged in → Auto-approve (no login screen!) →
Redirect back with authorization code →
Exchange code for access token (in browser) →
Store access token → Call Edge Function with token
```

#### How It Works

**First Time User Opens Dashboard**:
```javascript
// 1. Generate PKCE verifier & challenge
const codeVerifier = generateRandomString(64)
const codeChallenge = await sha256(codeVerifier)

// 2. Redirect to Keycloak
window.location.href =
  'https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/auth' +
  `?client_id=dashboard` +
  `&redirect_uri=${encodeURIComponent(callbackUrl)}` +
  `&response_type=code` +
  `&code_challenge=${codeChallenge}` +
  `&code_challenge_method=S256`

// 3. Keycloak checks: Is user logged in? YES → Skip login screen!
// 4. Keycloak redirects back: ?code=ABC123

// 5. Exchange code for tokens
const response = await fetch(
  'https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/token',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code: 'ABC123',
      redirect_uri: callbackUrl,
      client_id: 'dashboard',
      code_verifier: codeVerifier
    })
  }
)

const tokens = await response.json()
// {
//   access_token: "eyJhbGc...",
//   refresh_token: "eyJhbGc...",
//   expires_in: 3600
// }

// 6. Store tokens (IF storage persists)
localStorage.setItem('access_token', tokens.access_token)
localStorage.setItem('refresh_token', tokens.refresh_token)
```

**Subsequent Times**:
```javascript
// Check if token exists and not expired
const accessToken = localStorage.getItem('access_token')
if (accessToken && !isExpired(accessToken)) {
  // Use existing token - NO LOGIN NEEDED!
  loadDashboard(accessToken)
} else {
  // Token expired or missing - refresh or re-auth
  const refreshToken = localStorage.getItem('refresh_token')
  if (refreshToken) {
    // Refresh token (no user interaction)
    const newTokens = await refreshAccessToken(refreshToken)
    loadDashboard(newTokens.access_token)
  } else {
    // Re-authenticate (redirect to Keycloak)
    // But if still logged into rtwork → instant redirect back!
    startOAuth2Flow()
  }
}
```

#### Security

| Aspect | Rating | Notes |
|--------|--------|-------|
| **JWT Validation** | ⭐⭐⭐⭐⭐ | Standard Keycloak JWT |
| **PKCE Protection** | ⭐⭐⭐⭐⭐ | Prevents authorization code interception |
| **No Client Secret** | ⭐⭐⭐⭐⭐ | Safe for public clients (SPAs/mobile) |
| **Token Storage** | ⭐⭐⭐⭐ | localStorage (acceptable for access tokens) |
| **Refresh Tokens** | ⭐⭐⭐⭐⭐ | Long-lived, keeps user logged in |

#### User Experience

**IF localStorage persists** (web browser):
- First time: Instant redirect to Keycloak → Instant redirect back (< 1 second)
- Subsequent times: Dashboard loads immediately (no login)
- ⭐⭐⭐⭐⭐ (5/5) - Excellent UX

**IF localStorage doesn't persist** (mobile webview):
- Every time: Quick redirect to Keycloak → Instant redirect back (< 1 second)
- User never sees login form (if logged into rtwork)
- ⭐⭐⭐⭐ (4/5) - Minor annoyance (quick redirect), but seamless

#### Cost & Maintenance

- Infrastructure: $0 (Keycloak already exists, Edge Functions free tier)
- Maintenance: 0 hours (standard OAuth2, no custom logic)
- ⭐⭐⭐⭐⭐ (5/5)

#### Prerequisites

1. **Create OAuth2 client in Keycloak**:
   - Client ID: `dashboard` (or similar)
   - Client Type: Public (no client secret)
   - Valid Redirect URIs: `https://your-dashboard-url/callback`
   - Enable PKCE

2. **Verify Keycloak session is shared**:
   - User logged into rtwork app = Keycloak session active
   - OAuth2 flow should auto-approve without login screen

3. **Test storage persistence**:
   - Does localStorage persist when webview closes/reopens?
   - If NO → Every open requires quick redirect (still acceptable UX)

**Verdict**: ✅ **BEST OPTION** if Keycloak OAuth2 client can be configured

---

### Option 3: Supabase OTP (Separate Authentication)

**Status**: ✅ **VIABLE** - Fallback option

```
User opens dashboard → Enter email → Receive OTP code →
Enter OTP → Supabase auth session → Call Edge Function with Supabase JWT
```

#### How It Works

```javascript
// 1. User clicks "View Dashboard"
// 2. Show email input
const email = await promptForEmail()

// 3. Send OTP
await supabase.auth.signInWithOtp({
  email: email,
  options: { shouldCreateUser: false }  // Only existing users
})

// 4. User checks email, enters 6-digit code
const otp = await promptForOTP()

// 5. Verify OTP
const { data, error } = await supabase.auth.verifyOtp({
  email: email,
  token: otp,
  type: 'email'
})

// 6. Session established - store tokens
const { access_token, refresh_token } = data.session

// 7. Load dashboard with Supabase JWT
loadDashboard(access_token)
```

#### Security

- ⭐⭐⭐⭐⭐ (5/5) - Built-in Supabase Auth, very secure

#### User Experience

**First Time**:
- User already logged into rtwork
- Told to enter email + wait for OTP + enter code
- ⭐⭐☆☆☆ (2/5) - **Poor UX** (separate login when already authenticated!)

**With Session Persistence** (30-day refresh tokens):
- First time: Email + OTP (annoying)
- Next 30 days: Dashboard loads immediately
- ⭐⭐⭐⭐ (4/5) - Good after initial setup

**Without Session Persistence** (mobile webview):
- Every time: Email + OTP
- ⭐☆☆☆☆ (1/5) - **Terrible UX** (re-authenticate every time!)

#### Cost & Maintenance

- Infrastructure: $0 (Supabase free tier)
- Maintenance: 0 hours
- ⭐⭐⭐⭐⭐ (5/5)

#### Prerequisites

1. User email must exist in Supabase `users` table
2. Configure Supabase email template to send 6-digit OTP (see `SUPABASE_OTP_SETUP.md`)

**Verdict**: ✅ **FALLBACK OPTION** - Works but poor UX (separate login)

---

### Option 4: Backend-Issued Session Tokens with Cookies

**Status**: ✅ **VIABLE** - If cookies persist in mobile webview

```
User opens dashboard → Check if session cookie exists →
NO → One-time auth (OAuth2 OR OTP) →
Edge Function validates, issues long-lived session token as httpOnly cookie →
Subsequent requests auto-include cookie →
Edge Function validates cookie → Returns data
```

#### How It Works

**First Visit**:
```javascript
// 1. User opens dashboard - no cookie
// 2. Authenticate via OAuth2 or OTP (one time)
const keycloakToken = await authenticateViaOAuth2()

// 3. Call Edge Function with Keycloak token
const response = await fetch('/functions/v1/create-session', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${keycloakToken}` }
})

// 4. Edge Function validates Keycloak JWT, issues session cookie
// Set-Cookie: session_token=xyz123; HttpOnly; Secure; Max-Age=2592000
// (30-day expiration)
```

**Subsequent Visits**:
```javascript
// Browser/webview automatically sends cookie with every request
const response = await fetch('/functions/v1/dashboard-stats', {
  method: 'POST',
  credentials: 'include'  // Auto-sends cookie
})

// Edge Function validates session cookie
// No localStorage needed! Cookie persists natively
```

**Edge Function (Session Creation)**:
```typescript
// Create session endpoint
serve(async (req) => {
  // 1. Validate Keycloak JWT (one time)
  const keycloakJWT = extractJWT(req)
  const claims = await validateKeycloakJWT(keycloakJWT)

  // 2. Look up user
  const user = await lookupUser(claims.rtcloud_username)

  // 3. Create session token (30-day expiration)
  const sessionToken = await createJWT({
    user_id: user.id,
    username: user.username,
    exp: now() + 30 * 24 * 3600  // 30 days
  }, OUR_SECRET_KEY)

  // 4. Return with httpOnly cookie
  return new Response(JSON.stringify({ success: true }), {
    headers: {
      'Set-Cookie': `session_token=${sessionToken}; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000; Path=/`,
      'Content-Type': 'application/json'
    }
  })
})
```

**Edge Function (Data Endpoint)**:
```typescript
// Dashboard stats endpoint
serve(async (req) => {
  // 1. Extract session cookie
  const cookies = parseCookies(req.headers.get('Cookie'))
  const sessionToken = cookies.session_token

  if (!sessionToken) {
    return new Response('Unauthorized', { status: 401 })
  }

  // 2. Validate session token (our JWT, not Keycloak)
  const claims = await verifyJWT(sessionToken, OUR_SECRET_KEY)

  // 3. Fetch data for user
  const data = await fetchDashboardData(claims.user_id)

  return new Response(JSON.stringify(data))
})
```

#### Security

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Initial Auth** | ⭐⭐⭐⭐⭐ | Validates Keycloak JWT |
| **Session Tokens** | ⭐⭐⭐⭐ | Custom JWT (secure if key protected) |
| **HttpOnly Cookies** | ⭐⭐⭐⭐⭐ | Immune to XSS attacks |
| **SameSite** | ⭐⭐⭐⭐⭐ | Prevents CSRF |
| **Secret Management** | ⭐⭐⭐⭐ | Need to protect signing key |

#### User Experience

**IF cookies persist in mobile webview**:
- First time: Quick OAuth2/OTP (one-time setup)
- Next 30 days: Dashboard loads immediately
- ⭐⭐⭐⭐⭐ (5/5) - Excellent UX

**IF cookies don't persist**:
- Same as Option 3 (re-authenticate every time)
- ⭐☆☆☆☆ (1/5) - Poor UX

#### Cost & Maintenance

- Infrastructure: $0 (Edge Functions)
- Maintenance: Low (manage JWT signing key rotation)
- ⭐⭐⭐⭐ (4/5)

#### Prerequisites

1. **Verify cookies persist** in rtwork mobile webview
2. Manage JWT signing key securely (store in Supabase secrets)
3. Implement token refresh logic

**Verdict**: ✅ **GOOD OPTION** if cookies work in mobile webview

---

### Option 5: Native App Bridge for Token Storage

**Status**: ⚠️ **REQUIRES rtwork DEVELOPER COOPERATION**

```
User opens dashboard → JavaScript calls App.getAuthToken() →
Native app returns stored token → Use token for API calls
```

#### How It Works

**rtwork developer adds bridge functions**:
```swift
// iOS Native Code
@objc func getAuthToken(_ callback: String) {
    // Retrieve token from iOS Keychain (persistent, secure)
    let token = KeychainHelper.retrieve("dashboard_token")
    webView.evaluateJavaScript("\(callback)('\(token)')")
}

@objc func setAuthToken(_ token: String) {
    // Store in iOS Keychain
    KeychainHelper.save("dashboard_token", token)
}
```

**Dashboard JavaScript**:
```javascript
// Initial auth (OAuth2 or OTP)
const tokens = await authenticateFirstTime()

// Store via native bridge
if (window.App && App.setAuthToken) {
  App.setAuthToken(tokens.access_token)  // Persists natively
}

// Load dashboard
function loadDashboard() {
  if (window.App && App.getAuthToken) {
    // Get token from native storage
    App.getAuthToken((token) => {
      fetch('/functions/v1/dashboard-stats', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
    })
  }
}
```

#### Security

- ⭐⭐⭐⭐⭐ (5/5) - Native keychain storage is highly secure

#### User Experience

- First time: One-time auth setup
- Subsequent times: Dashboard loads immediately (token from keychain)
- ⭐⭐⭐⭐⭐ (5/5) - Excellent UX

#### Cost & Maintenance

- Infrastructure: $0
- Maintenance: 0 hours (after implementation)
- rtwork developer effort: ~4-8 hours (one-time)
- ⭐⭐⭐⭐ (4/5)

#### Prerequisites

1. **rtwork developer must implement**:
   - `App.setAuthToken(token)`
   - `App.getAuthToken(callback)`
2. Native storage (iOS Keychain, Android Keystore)

**Verdict**: ✅ **BEST UX** but requires rtwork developer cooperation (may not be willing)

---

### Option 6: Middleman Hybrid (n8n/Kestra Pass-Through)

**Status**: ⚠️ **VIABLE but against “no middleman” goal**

**Flow**:
```
rtwork app —(App.callApi includeToken=true)→ n8n/Kestra (allowed host)
→ Forwards request to Supabase Edge Function with Authorization header intact
→ Supabase Edge validates Keycloak JWT → Returns data → n8n/Kestra relays back
```

**Notes**:
- Uses existing allowlist (automation.rta.vn), so the Keycloak token arrives.
- Adds a hop and infra cost/ops burden (kept minimal if pass-through only).
- Security aligns with Option 1 (JWT validated at Supabase), but reintroduces self-hosted surface.
- Distinguish from legacy middleman: legacy flow did full JWT validation + DB queries + aggregation in n8n/Kestra (no Edge). This pass-through version defers all logic to the Edge function, keeping the middle layer as a thin forwarder only.

**Verdict**: Acceptable as a stopgap if no Keycloak/bridge changes, but conflicts with direct-to-Supabase objective.

---

### Option 7: User-ID Filtering Only (No JWT)

**Status**: ❌ **NOT RECOMMENDED**

**Flow**:
```
rtwork app → Supabase Edge (verify_jwt=false)
→ Client sends user_id (UUID) in body/query
→ Edge filters by user_id without validating JWT
→ Returns data
```

**Notes**:
- Assumptions already considered: user_id not intentionally exposed in UI; users are non-tech; devices are single-user and not shared.
- Removes cryptographic auth; relies on secrecy of user_id (security by obscurity).
- UUIDs can be guessed/brute-forced or leaked via logs/links; an attacker could enumerate user_id values and retrieve others’ data.
- Even if users are “non-tech” and devices are single-user, IDs can leak via crash logs, screenshots, backups, rooted/emulated devices, or malicious apps on the same device. If a device is lost/stolen, the `user_id` can be harvested and reused indefinitely.
- No replay protection, no expiration, no issuer/audience checks; any request with a user_id is treated as authentic.
- Role checks don’t prove identity; they only shape the response after trusting the caller’s claimed ID.
- Violates primary security requirement (must validate identity via signed token).

**Verdict**: Do not use; fails security requirements.

---

## Complete Comparison Matrix

| Solution | Security | UX (Web) | UX (Mobile) | Cost | Maintenance | Dependencies | Overall |
|----------|----------|----------|-------------|------|-------------|--------------|---------|
| **Option 1: App.callApi** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ Blocked (supabase.co not whitelisted; allowlist change likely rejected) | ❌ Not viable |
| **Option 2: OAuth2 PKCE** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Keycloak only (blocked: no client/redirect changes allowed) | ❌ Blocked |
| **Option 3: Supabase OTP** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | None | ⚠️ Fallback |
| **Option 4: Cookie Sessions** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❓ Untested | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Cookie support | ⚠️ If cookies work |
| **Option 5: Native Bridge** | ⭐⭐⭐⭐⭐ | N/A | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | rtwork developer (new bridge features unlikely approved) | ❌ Effectively blocked |
| **Option 6: Middleman (Kestra/n8n) Pass-Through** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | Self-hosted infra (allowed host); legacy full-processing middleman is excluded | ⚠️ Stopgap only |
| **Option 7: User-ID Only (No JWT)** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | None | ❌ Not recommended |
| **Legacy Middleman (Full Processing)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ | Self-hosted infra (JWT validation + DB + aggregation in n8n/Kestra, no Edge) | ❌ Excluded (cost/ops; contradicts direct-to-Supabase goal) |

### User Experience Scenarios

#### Scenario A: localStorage Persists (Web Browser, Some Mobile Webviews)

| Solution | First Visit | Second Visit | 10th Visit |
|----------|-------------|--------------|------------|
| OAuth2 PKCE | Quick redirect (1s) | Instant load | Instant load |
| Supabase OTP | Email + OTP (60s) | Instant load | Instant load |
| Cookie Sessions | OAuth2/OTP (1-60s) | Instant load | Instant load |

**Winner**: OAuth2 PKCE (best first-time UX)

#### Scenario B: localStorage Doesn't Persist (Mobile Webview)

| Solution | First Visit | Second Visit | 10th Visit |
|----------|-------------|--------------|------------|
| OAuth2 PKCE | Quick redirect (1s) | Quick redirect (1s) | Quick redirect (1s) |
| Supabase OTP | Email + OTP (60s) | Email + OTP (60s) | Email + OTP (60s) |
| Cookie Sessions | OAuth2/OTP (1-60s) | Instant or Auth | Instant or Auth |
| Native Bridge | OAuth2/OTP (1-60s) | Instant load | Instant load |

**Winner**: OAuth2 PKCE (if Keycloak session active) or Native Bridge (if available)

---

## Decision Tree

```
START: Need authentication for dashboard

├─ CAN rtwork developer add App.setAuthToken/getAuthToken bridge?
│  ├─ YES → ✅ Option 5: Native Bridge (BEST UX)
│  └─ NO → Continue
│
├─ DO cookies persist in mobile webview?
│  ├─ UNKNOWN → Test it!
│  ├─ YES → ✅ Option 4: Cookie Sessions (GOOD UX)
│  └─ NO → Continue
│
├─ CAN we create OAuth2 client in Keycloak?
│  ├─ YES → Does Keycloak session persist across webview opens?
│  │  ├─ YES → ✅ Option 2: OAuth2 PKCE (RECOMMENDED - Best balance)
│  │  └─ NO → ⚠️ Option 2 still viable but requires redirect each time
│  │
│  └─ NO → ✅ Option 3: Supabase OTP (FALLBACK - Poor UX but secure)
```

---

## Recommended Implementation Plan

### Phase 1: Investigation (Week 1)

**Day 1-2: Test Storage Capabilities**
```javascript
// Test localStorage persistence
localStorage.setItem('test', 'value')
// Close webview, reopen
console.log(localStorage.getItem('test'))  // null or "value"?

// Test cookie persistence
document.cookie = "test=value; max-age=86400"
// Close webview, reopen
console.log(document.cookie)  // Contains "test=value"?

// Test native bridge availability
console.log(typeof App.setAuthToken)  // "function" or "undefined"?
```

**Day 3-4: Confirm Keycloak OAuth2 Support**
- Check if Keycloak client can be created with:
  - Client Type: Public
  - Grant Type: Authorization Code
  - PKCE: Required
  - Valid Redirect URIs: Dashboard URL

**Day 5: Choose Solution**
Based on test results:
- localStorage + cookies persist → **Option 2 (OAuth2)**
- Only cookies persist → **Option 4 (Cookie Sessions)**
- Nothing persists, no native bridge → **Option 3 (OTP)** or negotiate with rtwork developer

### Phase 2: Implementation (Week 2-3)

**If Option 2 (OAuth2 PKCE)** - See `RTWORK_OAUTH2_INTEGRATION.md`

**If Option 3 (OTP)** - See `RTWORK_APP_INTEGRATION.md`

**If Option 4 (Cookie Sessions)** - Hybrid approach:
1. Implement OAuth2 for initial auth
2. Issue session cookie after validation
3. Use cookie for subsequent requests

### Phase 3: Testing & Rollout (Week 4)

Same gradual rollout as before:
- Beta users: 10%
- Canary: 25%
- Gradual: 50%, 75%, 100%
- Monitor error rates, UX feedback

---

## Security Best Practices (All Options)

### JWT Validation

```typescript
// ALWAYS verify JWT signature
const { payload } = await jose.jwtVerify(token, JWKS, {
  issuer: EXPECTED_ISSUER,
  audience: EXPECTED_AUDIENCE,
  clockTolerance: 30
})

// NEVER just decode without verifying
// const payload = JSON.parse(atob(token.split('.')[1]))  // ❌ DANGEROUS
```

### Token Storage

| Storage Method | Security | Persistence | Use Case |
|----------------|----------|-------------|----------|
| localStorage | ⚠️ Vulnerable to XSS | Yes | Access tokens (short-lived) |
| sessionStorage | ⚠️ Vulnerable to XSS | No | Temporary data |
| httpOnly Cookie | ✅ XSS-safe | Yes | Session tokens |
| Native Keychain | ✅ Most secure | Yes | Long-lived tokens |

### Defense in Depth

```typescript
// Edge Function should:
// 1. Validate token signature
// 2. Check expiration
// 3. Verify issuer/audience
// 4. Look up user in database
// 5. Check user status (active, not banned)
// 6. Query with service key BUT scope to validated user
// 7. Return only user's own data

// Example:
const claims = await validateJWT(token)  // Layer 1
const user = await getUser(claims.sub)    // Layer 2
if (!user || user.status !== 'active') {  // Layer 3
  throw new Error('Unauthorized')
}
const data = await fetchData(user.id)     // Layer 4: Scoped query
```

---

## Cost Analysis (3-Year TCO)

### All Options vs Current Kestra

| Solution | Year 1 | Year 2-3 | Total 3Y | vs Kestra Savings |
|----------|--------|----------|----------|-------------------|
| **Kestra (Current)** | $10,000 | $9,720/y | $29,440 | Baseline |
| **OAuth2 PKCE** | $640 | $0/y | $640 | **$28,800 saved** |
| **Supabase OTP** | $640 | $0/y | $640 | **$28,800 saved** |
| **Cookie Sessions** | $640 | $0/y | $640 | **$28,800 saved** |
| **Native Bridge** | $1,280* | $0/y | $1,280 | **$28,160 saved** |

*Assumes rtwork developer charges for implementing bridge functions

**All Supabase Edge Function options save ~98% over 3 years!**

---

## Final Recommendation

### Primary Recommendation: **Option 2 (OAuth2 PKCE)**

**Current status**: Blocked under current constraints (no Keycloak client changes, no redirect URI). Requires Keycloak admin cooperation to activate.

**Rationale**:
1. ✅ **True SSO** - If user logged into rtwork, Keycloak auto-approves
2. ✅ **Standard protocol** - OAuth2 is industry best practice
3. ✅ **No separate login** - Seamless redirect flow
4. ✅ **Good UX even without persistence** - Quick redirect (1 second)
5. ✅ **Secure** - Standard JWT validation
6. ✅ **Zero cost** - Keycloak already exists, Edge Functions free
7. ✅ **No dependencies** - Doesn't require rtwork developer cooperation (once Keycloak client is configured; currently blocked)

**User Experience**:
- With localStorage: Instant load (after first quick redirect)
- Without localStorage: Quick redirect each time (1s, no login form visible)
- **Either way better than OTP!**

### Fallback: **Option 3 (Supabase OTP)**

If OAuth2 can't be configured in Keycloak:
- Use OTP with 30-day refresh tokens
- First-time setup is annoying, but then smooth for 30 days
- On mobile without persistence: Poor UX but still functional

### Don't Pursue: **Option 5 (Native Bridge)**

Unless rtwork developer volunteers:
- Requires their time/effort
- They already rejected simpler request (whitelist)
- Unlikely to agree to implement custom bridge functions

---

## Next Steps

1. ✅ **Test storage capabilities** in rtwork mobile webview (Day 1-2)
2. ✅ **Contact Keycloak admin** to create OAuth2 client (Day 3)
3. ✅ **Implement Option 2** if OAuth2 possible, else Option 3 (Week 2)
4. ✅ **Deploy and test** with beta users (Week 3)
5. ✅ **Gradual rollout** to all users (Week 4)
6. ✅ **Decommission Kestra** after 30-day safety period

---

**Document Version**: 3.0 (Final with OAuth2 Analysis)
**Last Updated**: 2026-01-12
**Status**: Ready for Implementation
**Next Review**: After Phase 1 testing
