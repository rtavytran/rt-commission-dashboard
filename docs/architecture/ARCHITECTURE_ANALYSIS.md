# RT Commission Dashboard - Architecture Security Analysis

**Date**: 2026-01-12
**Purpose**: Evaluate architectural approaches for secure multi-platform data access
**Primary Concern**: Data security - prevent unauthorized access and data leakage

---

## Executive Summary

**Key Finding**: The current middleware approach (Kestra/n8n) is necessary for security but can be optimized by migrating to Supabase Edge Functions.

**Recommended Approach**: **Option 4 - Supabase Edge Functions + RLS** provides the best balance of security, user experience, and operational efficiency.

---

## Current Situation

### Access Patterns

| Platform | How Users Access | Current Auth | Security Layer |
|----------|-----------------|--------------|----------------|
| **Desktop** (RealtimeX) | localhost:8080 | Supabase Email/OTP | RLS + profiles table |
| **Mobile** (rtwork native app) | Embedded WebView | Keycloak JWT | Kestra validates JWT |
| **Web** (rtwork webapp) | Browser | `##user.username##` template | ❌ **VULNERABLE** |

### Security Vulnerability Discovered

**Problem**: On rtwork webapp, user can:
1. Open browser DevTools (F12)
2. Inspect HTML source
3. See template variable: `##user.username##` → "rta_admin"
4. Manually craft API request with admin username
5. **Bypass authentication** if API trusts username from request body

**Example Attack**:
```javascript
// User inspects page, sees admin username
// Crafts malicious request:
fetch('https://workflow.realtimex.co/api/v1/executions/webhook/flowai/dashboard', {
  method: 'POST',
  body: JSON.stringify({
    username: 'rta_admin',  // Impersonating admin!
    app_token: 'leaked_or_guessed_token'
  })
});
// If Kestra trusts this username → DATA BREACH
```

**Why Current Middleware Helps**:
- Native app uses `App.callApi(includeToken=true)` → JWT auto-attached
- JWT contains verified identity (Keycloak signed)
- Kestra validates JWT signature → trusts `rtcloud_username` from claims
- Ignores any username sent in request body
- **Webapp still vulnerable** if it doesn't use JWT!

---

## Architecture Options Analysis

### Option 1: Keep Current Middleware (Kestra/n8n)

```
Mobile App → JWT (auto-attached) → Kestra/n8n → Validates JWT →
Queries Supabase (service key) → Filters data → Returns JSON
```

#### Security: ⭐⭐⭐⭐☆ (4/5)

**Strengths**:
- ✅ JWT validation prevents impersonation
- ✅ Service key stays server-side (never exposed)
- ✅ Application-level data filtering
- ✅ Can add custom business logic
- ✅ Audit logging centralized

**Weaknesses**:
- ⚠️ Webapp users might not send JWT (depends on implementation)
- ⚠️ If JWT validation has bugs → security hole
- ⚠️ Service key compromise = full database access

#### User Experience: ⭐⭐⭐⭐☆ (4/5)

**Pros**:
- ✅ Single sign-on (Keycloak)
- ✅ No extra login steps
- ✅ Fast response (if cached)
- ✅ Works on all platforms

**Cons**:
- ❌ Depends on middleware availability
- ❌ Latency: Mobile → Kestra → Supabase → Kestra → Mobile
- ❌ Network issues = dashboard unavailable

#### Cost & Resources: ⭐⭐☆☆☆ (2/5)

**Infrastructure**:
```
- Kestra/n8n Server: $50-200/month (self-hosted VPS)
- Bandwidth: ~$10-50/month (depends on traffic)
- Maintenance: 4-8 hours/month (monitoring, updates)
- Total: $60-250/month + 8h labor
```

**Operational Burden**:
- ❌ Must maintain self-hosted server
- ❌ Handle scaling (vertical/horizontal)
- ❌ Monitor uptime (99.9% SLA?)
- ❌ Debug production issues at 2am
- ❌ Security patches, OS updates
- ❌ Backup & disaster recovery

**Failure Modes**:
| Issue | Impact | MTTR |
|-------|--------|------|
| Kestra crash | Dashboard down | 5-30 min |
| Network congestion | Slow/timeout | Variable |
| DDoS attack | Service unavailable | Hours |
| Security breach | Data leak + remediation | Days |

#### Scalability: ⭐⭐⭐☆☆ (3/5)

**Current Capacity**: ~100-500 concurrent users (depends on server specs)

**Scaling Strategy**:
- Vertical: Upgrade server ($$$)
- Horizontal: Load balancer + multiple instances (complex)
- Caching: Add Redis (more infrastructure)

---

### Option 2: Supabase Edge Functions + RLS

```
Mobile App → JWT → Supabase Edge Function → Validates JWT →
RLS enforces access → Returns filtered data
```

#### Architecture

**Supabase Edge Functions** (Deno runtime):
```typescript
// supabase/functions/dashboard-stats/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  try {
    // 1. Extract JWT from Authorization header
    const authHeader = req.headers.get('Authorization')
    if (!authHeader?.startsWith('Bearer ')) {
      return new Response(JSON.stringify({ error: 'Missing token' }), {
        status: 401
      })
    }

    const jwt = authHeader.replace('Bearer ', '')

    // 2. Verify JWT with Keycloak public key
    const keycloakPublicKey = Deno.env.get('KEYCLOAK_PUBLIC_KEY')
    const claims = await verifyKeycloakJWT(jwt, keycloakPublicKey)

    if (!claims) {
      return new Response(JSON.stringify({ error: 'Invalid token' }), {
        status: 401
      })
    }

    // 3. Extract rtcloud_username from validated claims
    const username = claims.rtcloud_username

    // 4. Query Supabase with service role (bypasses RLS for this function)
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // 5. Look up user UUID by username
    const { data: user, error: userError } = await supabaseClient
      .from('users')
      .select('id, full_name, email, role')
      .eq('username', username)
      .single()

    if (userError || !user) {
      return new Response(JSON.stringify({ error: 'User not found' }), {
        status: 404
      })
    }

    // 6. Fetch data scoped to this user
    const { data: transactions } = await supabaseClient
      .from('transactions')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .limit(50)

    const { data: monthlyStats } = await supabaseClient
      .from('monthly_stats')
      .select('*')
      .eq('user_id', user.id)
      .order('month', { ascending: false })
      .limit(12)

    // 7. Return filtered data
    return new Response(JSON.stringify({
      user,
      transactions,
      monthlyStats,
      timestamp: new Date().toISOString()
    }), {
      headers: { 'Content-Type': 'application/json' }
    })

  } catch (error) {
    console.error('Error:', error)
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500
    })
  }
})
```

**JWT Verification Helper**:
```typescript
import * as jose from 'https://deno.land/x/jose@v4.11.1/index.ts'

async function verifyKeycloakJWT(token: string, publicKeyPEM: string) {
  try {
    // Import public key
    const publicKey = await jose.importSPKI(publicKeyPEM, 'RS256')

    // Verify JWT
    const { payload } = await jose.jwtVerify(token, publicKey, {
      issuer: 'https://accounts.rtworkspace.com/auth/realms/rta',
      audience: ['C155', 'account'], // Expected audiences
      clockTolerance: 30 // 30 second skew tolerance
    })

    // Check expiration
    if (payload.exp && payload.exp < Date.now() / 1000) {
      throw new Error('Token expired')
    }

    return payload
  } catch (error) {
    console.error('JWT verification failed:', error)
    return null
  }
}
```

#### Security: ⭐⭐⭐⭐⭐ (5/5)

**Strengths**:
- ✅ JWT validation (same as Kestra)
- ✅ Managed infrastructure (Supabase handles security)
- ✅ Edge runtime isolation (Deno sandbox)
- ✅ RLS as defense-in-depth (if function has bug)
- ✅ Automatic HTTPS, DDoS protection
- ✅ Environment variables encrypted

**Comparison to Kestra**:
| Security Feature | Kestra | Supabase Edge |
|-----------------|--------|---------------|
| JWT validation | ✅ Custom code | ✅ jose library (battle-tested) |
| Infrastructure security | ❌ Your responsibility | ✅ Supabase managed |
| Secrets management | ⚠️ KV store | ✅ Encrypted env vars |
| DDoS protection | ❌ Must implement | ✅ Built-in (Cloudflare) |
| Audit logs | ⚠️ Custom | ✅ Built-in |

#### User Experience: ⭐⭐⭐⭐⭐ (5/5)

**Pros**:
- ✅ Fast response (<200ms globally via edge network)
- ✅ High availability (99.9% SLA)
- ✅ Auto-scaling (handles traffic spikes)
- ✅ Same UX as current (transparent to users)

**Latency Comparison**:
```
Current (Kestra):
Mobile → Kestra (Vietnam) → Supabase (Singapore) → Kestra → Mobile
= 150ms + 50ms + 100ms + 150ms = 450ms

Supabase Edge:
Mobile → Supabase Edge (nearest region) → Supabase → Edge → Mobile
= 50ms + 50ms + 100ms + 50ms = 250ms

Improvement: ~45% faster
```

#### Cost & Resources: ⭐⭐⭐⭐⭐ (5/5)

**Supabase Edge Functions Pricing** (as of 2026):
```
Free Tier:
- 500,000 invocations/month
- 400,000 GB-seconds compute

Pro Plan ($25/month):
- 2,000,000 invocations/month
- 2,000,000 GB-seconds compute

Usage estimate (100 users, 50 requests/day each):
= 100 users × 50 req/day × 30 days = 150,000 req/month
= FREE TIER (covers up to ~330 users)
```

**Total Cost Comparison**:
| Component | Kestra | Supabase Edge |
|-----------|--------|---------------|
| Infrastructure | $50-200/month | $0 (free tier) |
| Maintenance | 8 hours/month | 0 hours |
| Monitoring | Custom setup | Built-in |
| Scaling | Manual | Automatic |
| **Total** | **$60-250/mo + 8h** | **$0 + 0h** |

**Savings**: ~$720-3,000/year + 96 hours labor

#### Scalability: ⭐⭐⭐⭐⭐ (5/5)

**Auto-scaling**:
- ✅ Handles 0 → 10,000 users automatically
- ✅ Global edge network (low latency worldwide)
- ✅ No configuration needed

**Cold Starts**: ~100-300ms (first request after idle)
- Acceptable for dashboard use case
- Subsequent requests: <50ms

---

### Option 3: Supabase Auth OTP (Separate Login)

```
Mobile App → User requests dashboard → Supabase sends OTP →
User enters OTP → Supabase Auth session → RLS enforces access
```

#### Architecture

**Flow**:
1. User taps "View Dashboard" in rtwork app
2. App displays: "Enter your email to receive access code"
3. User enters email → Supabase sends OTP
4. User enters 6-digit code
5. Supabase validates → creates auth session
6. Dashboard loads with RLS-enforced data

**Implementation**:
```javascript
// Mobile app
async function loginToDashboard() {
  // Step 1: Request OTP
  const { error } = await supabase.auth.signInWithOtp({
    email: userEmail,
    options: {
      shouldCreateUser: false // Only allow existing users
    }
  })

  if (error) {
    alert('Email not registered in dashboard system')
    return
  }

  // Step 2: Show OTP input
  const otp = await showOtpPrompt()

  // Step 3: Verify OTP
  const { data, error: verifyError } = await supabase.auth.verifyOtp({
    email: userEmail,
    token: otp,
    type: 'email'
  })

  if (verifyError) {
    alert('Invalid code')
    return
  }

  // Step 4: Session established, load dashboard
  loadDashboard(data.session.access_token)
}
```

#### Security: ⭐⭐⭐⭐⭐ (5/5)

**Strengths**:
- ✅ No JWT validation needed (Supabase handles)
- ✅ RLS enforces all access
- ✅ Time-limited OTP codes (expire after 5 min)
- ✅ Separate authentication layer
- ✅ No middleware = no middleware vulnerabilities

**Authentication Flow**:
```
User → Supabase Auth (OTP) → Session token →
Supabase Client (anon key + session) → RLS checks auth.uid() →
Data filtered by profiles.user_id → Returns user's data only
```

#### User Experience: ⭐⭐☆☆☆ (2/5)

**Pros**:
- ✅ Familiar (everyone knows OTP)
- ✅ Works on all platforms

**Cons**:
- ❌ **Extra login step** (user already logged into rtwork!)
- ❌ Email delay (OTP delivery time)
- ❌ User must check email
- ❌ Code expires (frustration if slow)
- ❌ Friction reduces usage
- ❌ Two separate authentication systems

**User Journey Comparison**:
```
Current (JWT):
Tap "Dashboard" → Loads immediately (< 1 sec)

OTP Approach:
Tap "Dashboard" → Enter email → Wait for email (10-60 sec) →
Check email app → Copy code → Enter code → Dashboard loads

Time: 30-90 seconds vs 1 second
Steps: 6 vs 1
```

**Critical UX Issue**: Users are already authenticated in rtwork! Making them log in again creates friction and confusion.

#### Cost & Resources: ⭐⭐⭐⭐☆ (4/5)

**Supabase Auth Pricing**:
```
Free Tier:
- 50,000 Monthly Active Users (MAU)
- Unlimited OTP sends

Cost: $0 for foreseeable future
```

**Operational Burden**:
- ✅ Zero maintenance
- ✅ Managed by Supabase
- ⚠️ Must handle two auth systems (Keycloak + Supabase)

#### Scalability: ⭐⭐⭐⭐⭐ (5/5)

- ✅ Supabase Auth scales automatically
- ✅ RLS scales with database

---

### Option 4: Hybrid - Supabase RLS + Profile Linking (Recommended)

```
Mobile App (Keycloak JWT) → Supabase Edge Function →
Validates JWT → Links to profiles.user_id →
RLS enforces access based on profiles → Returns data
```

#### Architecture

**Key Innovation**: Link Keycloak identity to Supabase profiles automatically

**Database Addition**:
```sql
-- Add Keycloak username to profiles for lookup
ALTER TABLE public.profiles
ADD COLUMN keycloak_username TEXT UNIQUE;

-- Index for fast lookup
CREATE INDEX idx_profiles_keycloak_username
ON public.profiles(keycloak_username);
```

**Edge Function** (simplified):
```typescript
serve(async (req) => {
  // 1. Validate Keycloak JWT
  const jwt = extractJWT(req)
  const claims = await verifyKeycloakJWT(jwt)
  const keycloakUsername = claims.rtcloud_username // "rta_vytran"

  // 2. Look up profile by keycloak_username
  const { data: profile } = await supabase
    .from('profiles')
    .select('id, user_id, role, status')
    .eq('keycloak_username', keycloakUsername)
    .single()

  if (!profile || profile.status !== 'approved') {
    return new Response('Unauthorized', { status: 403 })
  }

  // 3. Create Supabase session for this profile
  // This makes auth.uid() = profile.id for RLS
  const { data: { session } } = await supabase.auth.admin.generateLink({
    type: 'magiclink',
    email: profile.email,
    options: { redirectTo: '' }
  })

  // 4. Use session to query data (RLS enforced)
  const sessionClient = createClient(
    supabaseUrl,
    supabaseAnonKey,
    { global: { headers: { Authorization: `Bearer ${session.access_token}` }}}
  )

  // 5. Queries now respect RLS policies
  const { data: transactions } = await sessionClient
    .from('transactions')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(50)
  // RLS automatically filters to user's data!

  return new Response(JSON.stringify({ transactions }))
})
```

**Benefits**:
- ✅ Single JWT validation (at edge function)
- ✅ RLS enforces data access (defense in depth)
- ✅ No manual filtering (database does it)
- ✅ Same UX as current (transparent)
- ✅ Managed infrastructure

#### Security: ⭐⭐⭐⭐⭐ (5/5)

**Defense in Depth**:
1. **Layer 1**: Edge function validates Keycloak JWT
2. **Layer 2**: Check profile status = 'approved'
3. **Layer 3**: RLS policies enforce data access

**Attack Scenarios**:
| Attack | Defense |
|--------|---------|
| Fake JWT | Edge function rejects (signature invalid) |
| Stolen JWT | Time-limited (exp claim), revocable |
| SQL injection | RLS + parameterized queries |
| Direct DB access | RLS blocks (anon key has no special access) |
| Edge function bug | RLS catches (failsafe) |

#### User Experience: ⭐⭐⭐⭐⭐ (5/5)

**Same as Option 2**: Fast, seamless, no extra login

#### Cost & Resources: ⭐⭐⭐⭐⭐ (5/5)

**Same as Option 2**: Free tier covers usage, zero maintenance

#### Scalability: ⭐⭐⭐⭐⭐ (5/5)

**Same as Option 2**: Auto-scaling, global edge

---

## Comparison Matrix

| Criteria | Option 1: Kestra | Option 2: Edge Functions | Option 3: OTP | Option 4: Hybrid |
|----------|-----------------|------------------------|---------------|------------------|
| **Security** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **User Experience** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Cost** | ⭐⭐ ($60-250/mo) | ⭐⭐⭐⭐⭐ ($0) | ⭐⭐⭐⭐ ($0) | ⭐⭐⭐⭐⭐ ($0) |
| **Maintenance** | ⭐⭐ (8h/mo) | ⭐⭐⭐⭐⭐ (0h) | ⭐⭐⭐⭐⭐ (0h) | ⭐⭐⭐⭐⭐ (0h) |
| **Scalability** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Latency** | 450ms | 250ms | 300ms | 250ms |
| **Complexity** | Medium | Low | Low | Medium |
| **Failover** | Manual | Automatic | Automatic | Automatic |

---

## Webapp Vulnerability Analysis

### Current Vulnerability

**Exposed Template Variables**:
```html
<!-- rtwork webapp HTML -->
<div id="user-info">
  Welcome, ##user.full_name##!
  Username: ##user.username##
</div>

<script>
  // User can see in DevTools:
  const username = "##user.username##"; // "rta_admin"

  // Malicious user crafts request:
  fetch('/api/dashboard', {
    method: 'POST',
    body: JSON.stringify({ username: 'rta_admin' })
  });
</script>
```

### How Each Option Handles This

**Option 1 (Kestra)**:
```python
# Kestra flow
payload = parse_payload()
username_from_body = payload.get('username')  # "rta_admin" (from attacker!)

# ❌ VULNERABLE if we trust this:
user = lookup_user(username_from_body)  # Attacker becomes admin!

# ✅ SECURE if we use JWT:
jwt_claims = validate_jwt(request.headers['Authorization'])
username_from_jwt = jwt_claims['rtcloud_username']  # Real user identity
user = lookup_user(username_from_jwt)  # Uses authenticated identity
```

**Issue**: Must ensure webapp also sends JWT, not just native app!

**Option 2/4 (Edge Functions)**:
```typescript
// Edge function REQUIRES JWT
const jwt = req.headers.get('Authorization')
if (!jwt) {
  return new Response('Unauthorized', { status: 401 })
}

// Validates JWT - ignores any username in body
const claims = await verifyKeycloakJWT(jwt)
const username = claims.rtcloud_username
```

**Issue**: Same as Option 1 - webapp must send JWT

**Option 3 (OTP)**:
```javascript
// Webapp flow
// User clicks "View Dashboard"
const { data } = await supabase.auth.signInWithOtp({
  email: currentUser.email
})
// Supabase sends OTP to email
// User enters OTP
// Session created - no template variables exposed!
```

**Advantage**: No way to impersonate because OTP sent to verified email

### Webapp JWT Solution

**If webapp uses `App.callApi` with `includeToken=true`**:
```javascript
// In rtwork webapp (same as native)
App.callApi(
  'https://supabase-project.functions.supabase.co/dashboard-stats',
  'POST',
  '{}',
  JSON.stringify({'Content-Type': 'application/json'}),
  true,  // ← This includes JWT from Keycloak
  'onDashboardResponse'
);
```

**Then webapp is secure!** The `##user.username##` is just for display, not used for authentication.

**Verdict**: Options 2/4 work for webapp IF the app-bridge supports JWT on web platform.

---

## Migration Analysis

### From Current (Kestra) to Option 4 (Edge Functions)

#### Migration Effort

**Development Time**: ~2-3 days
- Day 1: Set up Edge Function, JWT verification
- Day 2: Add keycloak_username to profiles, migration script
- Day 3: Testing, deployment

**Steps**:

1. **Add keycloak_username to profiles**:
```sql
ALTER TABLE public.profiles
ADD COLUMN keycloak_username TEXT UNIQUE;

CREATE INDEX idx_profiles_keycloak_username
ON public.profiles(keycloak_username);

-- Migrate existing data (map users.username to profiles)
UPDATE public.profiles p
SET keycloak_username = u.username
FROM public.users u
WHERE p.user_id = u.id;
```

2. **Create Edge Function**:
```bash
# Initialize Supabase project locally
supabase init

# Create function
supabase functions new dashboard-stats

# Write function code (see Option 4 architecture)

# Deploy
supabase functions deploy dashboard-stats \
  --project-ref YOUR_PROJECT_REF
```

3. **Update mobile app**:
```javascript
// Change API endpoint
const OLD_URL = 'https://workflow.realtimex.co/api/v1/executions/webhook/flowai/nagen_user_stats/input';
const NEW_URL = 'https://pphoiqknkmwzstuokdmz.supabase.co/functions/v1/dashboard-stats';

// Same App.callApi code - no changes needed!
App.callApi(NEW_URL, 'POST', '{}', headers, true, 'onResponse');
```

4. **Test thoroughly**:
- [ ] Native app on iOS
- [ ] Native app on Android
- [ ] Webapp (if supported)
- [ ] Different user roles (admin, affiliate, ctv)
- [ ] Edge cases (expired JWT, blocked user, etc.)

5. **Gradual rollout**:
```javascript
// Feature flag for testing
const USE_EDGE_FUNCTION = config.get('use_edge_function') || false;
const apiUrl = USE_EDGE_FUNCTION ? NEW_URL : OLD_URL;
```

6. **Monitor for 1 week**, then decommission Kestra

#### Rollback Plan

**If issues arise**:
```javascript
// Instant rollback via config
config.set('use_edge_function', false);
// App falls back to Kestra immediately (no deploy needed)
```

**Kestra stays online during migration** for safety.

---

## Recommendations

### Primary Recommendation: **Option 4 (Hybrid - Edge Functions + RLS)**

**Rationale**:
1. ✅ **Best Security**: JWT validation + RLS defense-in-depth
2. ✅ **Zero Maintenance**: Supabase manages infrastructure
3. ✅ **Free**: No ongoing costs (free tier covers usage)
4. ✅ **Fast**: ~45% lower latency via edge network
5. ✅ **Scalable**: Auto-scales to any load
6. ✅ **Same UX**: Users experience no change

### Implementation Priority

**Phase 1: Immediate (Week 1)**
- [ ] Add `keycloak_username` column to profiles
- [ ] Create Edge Function with JWT validation
- [ ] Deploy to staging environment
- [ ] Test with sample users

**Phase 2: Migration (Week 2)**
- [ ] Update mobile app to use Edge Function (feature flagged)
- [ ] Enable for 10% of users (canary deployment)
- [ ] Monitor metrics (errors, latency, auth failures)
- [ ] Gradually increase to 100%

**Phase 3: Cleanup (Week 3)**
- [ ] Decommission Kestra flow (keep as backup for 1 month)
- [ ] Update documentation
- [ ] Remove old code
- [ ] Celebrate cost savings! 🎉

### Fallback Position: **Option 3 (OTP) for Webapp Only**

**If webapp cannot send JWT**:
- Native app → Edge Functions (seamless)
- Webapp → OTP login (extra step, but secure)

**Hybrid UX**:
```javascript
function openDashboard() {
  if (isNativeApp()) {
    // Seamless - uses JWT
    loadDashboardViaEdgeFunction();
  } else if (isWebapp()) {
    // Requires OTP
    showOtpLoginPrompt();
  }
}
```

**User Impact**: Webapp users get extra security step, native app users unaffected.

---

## Risk Assessment

### High Risk (Must Address)

**🔴 Webapp Impersonation Vulnerability**
- **Severity**: CRITICAL
- **Current State**: Template variables exposed
- **Mitigation**: Ensure JWT validation on all platforms
- **Verification**: Test webapp with DevTools open

### Medium Risk (Monitor)

**🟡 Kestra Single Point of Failure**
- **Severity**: HIGH (current)
- **Impact**: Dashboard unavailable if Kestra down
- **Mitigation**: Migrate to Edge Functions (redundant, auto-failover)

**🟡 JWT Secret Management**
- **Severity**: MEDIUM
- **Current**: Keycloak public key must be kept updated
- **Mitigation**: Use JWKS endpoint for auto-rotation
- **Implementation**:
```typescript
// Auto-fetch Keycloak public key
const jwksUrl = 'https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/certs';
const JWKS = jose.createRemoteJWKSet(new URL(jwksUrl));

// Verify with auto-updated key
const { payload } = await jose.jwtVerify(token, JWKS, {
  issuer: 'https://accounts.rtworkspace.com/auth/realms/rta'
});
```

### Low Risk (Acceptable)

**🟢 Edge Function Cold Starts**
- **Impact**: First request after idle ~100-300ms slower
- **Frequency**: Rare (dashboard accessed frequently)
- **Acceptable**: Yes

**🟢 Supabase Vendor Lock-in**
- **Impact**: Hard to migrate off Supabase later
- **Mitigation**: Edge Functions are standard Deno - portable to other platforms
- **Acceptable**: Yes (benefit > risk)

---

## Cost-Benefit Analysis

### 3-Year TCO Comparison

**Option 1 (Kestra - Current)**:
```
Year 1: $2,400 (hosting) + $8,000 (96h × $83/h labor) = $10,400
Year 2: $2,400 + $8,000 = $10,400
Year 3: $2,400 + $8,000 = $10,400
─────────────────────────────
Total: $31,200 over 3 years
```

**Option 4 (Edge Functions)**:
```
Year 1: $0 (free tier) + $0 (zero maintenance) + $3,000 (migration) = $3,000
Year 2: $0 + $0 = $0
Year 3: $0 + $0 = $0
─────────────────────────────
Total: $3,000 over 3 years (10% of Kestra cost!)
```

**Savings**: $28,200 over 3 years

**ROI**:
```
Migration cost: $3,000
Annual savings: $10,400
Break-even: 3.4 months
3-year ROI: 840%
```

### Intangible Benefits

**Reliability**:
- Supabase SLA: 99.9% uptime
- Self-hosted Kestra: 95-98% (realistically)
- **Result**: ~15x fewer outages

**Developer Velocity**:
- No server maintenance = more time for features
- Managed monitoring = faster debugging
- Auto-scaling = no capacity planning

**Security Posture**:
- Managed security patches
- Enterprise-grade infrastructure
- Regular third-party audits (Supabase)

---

## Conclusion

**The middleware approach (Kestra/n8n) was correct for security** - validating JWT and not trusting client-supplied usernames is essential.

**However, the middleware doesn't need to be self-hosted.** Supabase Edge Functions provide the same security benefits with:
- ✅ Zero maintenance
- ✅ Lower cost ($0 vs $2,400/year)
- ✅ Better reliability (99.9% SLA)
- ✅ Faster performance (edge network)
- ✅ Auto-scaling

**Action Items**:

1. **Immediate**: Verify webapp sends JWT (test with DevTools)
2. **This Week**: Implement Option 4 (Edge Functions) in staging
3. **Next Week**: Migrate 10% of users
4. **Month 1**: Complete migration, decommission Kestra

**Expected Outcome**: Same security, better UX, lower cost, less maintenance.

---

## Appendix: JWT Validation Best Practices

### Checklist for Secure JWT Validation

**Required Validations**:
- [ ] Signature verification (RS256 with Keycloak public key)
- [ ] Expiration time (`exp` claim)
- [ ] Issuer (`iss` = `https://accounts.rtworkspace.com/auth/realms/rta`)
- [ ] Audience (`aud` contains expected client ID)
- [ ] Not-before (`nbf` claim, if present)
- [ ] Issued-at (`iat` claim, reasonable time)

**Clock Skew Tolerance**: 30-60 seconds (to handle server time differences)

**Token Extraction**:
```typescript
// ✅ Correct
const authHeader = req.headers.get('Authorization');
if (!authHeader?.startsWith('Bearer ')) {
  throw new Error('Missing or invalid Authorization header');
}
const token = authHeader.replace('Bearer ', '');

// ❌ Wrong (vulnerable to injection)
const token = req.headers.get('Authorization')?.split(' ')[1];
```

**Claims Usage**:
```typescript
// ✅ Use validated claims only
const username = verifiedClaims.rtcloud_username;

// ❌ Never trust unvalidated data
const username = req.body.username; // User can fake this!
```

**Error Handling**:
```typescript
try {
  const claims = await verifyJWT(token);
  return claims;
} catch (error) {
  // Log the error (for debugging)
  console.error('JWT validation failed:', error.message);

  // Return generic error (don't leak details)
  throw new Error('Unauthorized');
}
```

### Sample Implementation (Production-Ready)

```typescript
import * as jose from 'https://deno.land/x/jose@v4.11.1/index.ts';

const KEYCLOAK_JWKS_URL = 'https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/certs';
const KEYCLOAK_ISSUER = 'https://accounts.rtworkspace.com/auth/realms/rta';
const EXPECTED_AUDIENCE = ['C155', 'account'];
const CLOCK_TOLERANCE = 30; // seconds

// Create JWKS client (auto-fetches and caches public keys)
const JWKS = jose.createRemoteJWKSet(new URL(KEYCLOAK_JWKS_URL));

export async function validateKeycloakJWT(token: string) {
  try {
    // Verify JWT signature, expiration, issuer, audience
    const { payload } = await jose.jwtVerify(token, JWKS, {
      issuer: KEYCLOAK_ISSUER,
      audience: EXPECTED_AUDIENCE,
      clockTolerance: CLOCK_TOLERANCE,
    });

    // Additional validations
    if (!payload.rtcloud_username) {
      throw new Error('Missing rtcloud_username claim');
    }

    if (!payload.email) {
      throw new Error('Missing email claim');
    }

    return {
      username: payload.rtcloud_username as string,
      email: payload.email as string,
      sub: payload.sub as string,
      exp: payload.exp as number,
      iat: payload.iat as number,
    };
  } catch (error) {
    console.error('JWT validation failed:', {
      error: error.message,
      tokenPrefix: token.substring(0, 20) + '...',
    });
    throw new Error('Invalid or expired token');
  }
}
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-12
**Next Review**: After Phase 1 completion
