# Dashboard Stats Edge Function

Secure API endpoint for rtwork mobile/web app to fetch user dashboard data.

## Overview

This Edge Function:
- ✅ Validates Keycloak JWT from rtwork app
- ✅ Extracts user identity from JWT claims
- ✅ Queries Supabase with service key (scoped to authenticated user)
- ✅ Returns dashboard data (transactions, stats, summary)

## Security Model

```
rtwork app → Keycloak JWT → Edge Function validates JWT →
Uses service key → Queries Supabase → Returns filtered data
```

**Key Points**:
- JWT validation prevents impersonation
- Service key stays in Edge Function (never exposed to client)
- Data manually scoped to authenticated user
- CORS enabled for browser requests

## Environment Variables

Set these in Supabase Dashboard → Edge Functions → Configuration:

### Required (Manual Setup)

| Variable | Value | Description |
|----------|-------|-------------|
| `KEYCLOAK_ISSUER` | `https://accounts.rtworkspace.com/auth/realms/rta` | Keycloak realm URL |
| `KEYCLOAK_JWKS_URL` | `https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/certs` | Keycloak public key endpoint |

### Auto-Provided by Supabase

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service key with full database access |

## Deployment

### Prerequisites

1. Install Supabase CLI:
```bash
# macOS
brew install supabase/tap/supabase

# Windows
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase

# Linux
brew install supabase/tap/supabase
```

2. Login to Supabase:
```bash
supabase login
```

3. Link to your project:
```bash
cd D:\RTA\GitHub\rt-commission-dashboard
supabase link --project-ref pphoiqknkmwzstuokdmz
```

### Deploy Function

```bash
# Deploy to production
supabase functions deploy dashboard-stats

# Deploy with environment variables
supabase secrets set KEYCLOAK_ISSUER=https://accounts.rtworkspace.com/auth/realms/rta
supabase secrets set KEYCLOAK_JWKS_URL=https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/certs

# Verify deployment
supabase functions list
```

### Function URL

After deployment, your function will be available at:
```
https://pphoiqknkmwzstuokdmz.supabase.co/functions/v1/dashboard-stats
```

## Testing

### Test with curl (Local)

```bash
# Start local development server
supabase start
supabase functions serve dashboard-stats

# Get a real Keycloak JWT from rtwork app
# (Open browser DevTools → Network tab → Copy Authorization header)

# Test request
curl -X POST http://localhost:54321/functions/v1/dashboard-stats \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Test with curl (Production)

```bash
# Replace <JWT> with actual Keycloak JWT
curl -X POST https://pphoiqknkmwzstuokdmz.supabase.co/functions/v1/dashboard-stats \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Expected Response

```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "rta_vytran",
    "full_name": "Vy Tran",
    "email": "vytran@rtanalytics.vn",
    "role": "affiliate"
  },
  "summary": {
    "total_sales": 15000000,
    "total_commissions": 3000000,
    "transaction_count": 25,
    "current_month": {
      "month": "2026-01",
      "personal_sales_volume": 5000000,
      "total_commission": 1000000,
      ...
    }
  },
  "transactions": [
    {
      "id": "...",
      "amount": 1000000,
      "type": "retail_sales",
      "status": "approved",
      "created_at": "2026-01-12T10:30:00Z"
    },
    ...
  ],
  "monthly_stats": [
    {
      "month": "2026-01",
      "personal_sales_volume": 5000000,
      "total_commission": 1000000
    },
    ...
  ]
}
```

### Error Responses

**401 Unauthorized - Missing Token**:
```json
{
  "error": "Missing Authorization header"
}
```

**401 Unauthorized - Invalid Token**:
```json
{
  "error": "Invalid token signature"
}
```

**401 Unauthorized - Expired Token**:
```json
{
  "error": "Token expired. Please login again."
}
```

**404 Not Found - User Not in Database**:
```json
{
  "error": "User not found in database",
  "message": "Your account may not be set up yet. Please contact support.",
  "username": "rta_newuser"
}
```

## Integration with rtwork App

### JavaScript/TypeScript

```javascript
// rtwork app code
function loadDashboard() {
  App.callApi(
    'https://pphoiqknkmwzstuokdmz.supabase.co/functions/v1/dashboard-stats',
    'POST',
    '{}',
    JSON.stringify({'Content-Type': 'application/json'}),
    true,  // includeToken=true → Keycloak JWT auto-attached
    'onDashboardResponse'
  );
}

function onDashboardResponse(payload) {
  if (payload.status === 'error') {
    console.error('API Error:', payload.error);
    showError(payload.error);
    return;
  }

  try {
    const data = JSON.parse(payload.data);

    // Render dashboard
    document.getElementById('user-name').textContent = data.user.full_name;
    document.getElementById('total-sales').textContent = formatCurrency(data.summary.total_sales);
    document.getElementById('total-commission').textContent = formatCurrency(data.summary.total_commissions);

    renderTransactions(data.transactions);
    renderMonthlyChart(data.monthly_stats);

  } catch (e) {
    console.error('Parse error:', e);
    showError('Failed to parse response');
  }
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND'
  }).format(amount);
}
```

## Monitoring

### View Logs

```bash
# Real-time logs (local)
supabase functions logs dashboard-stats --follow

# Production logs (Supabase Dashboard)
# Navigate to: Edge Functions → dashboard-stats → Logs
```

### Key Metrics to Monitor

- **Error Rate**: Should be < 0.1%
- **Response Time**: P95 should be < 500ms
- **401 Errors**: Indicates JWT validation failures (expired tokens, etc.)
- **404 Errors**: Users not found in database (sync issue)
- **500 Errors**: Database query failures (investigate immediately)

## Troubleshooting

### Issue: "Missing rtcloud_username in token"

**Cause**: JWT from Keycloak doesn't have `rtcloud_username` claim

**Solution**:
1. Check Keycloak realm settings
2. Ensure custom claim `rtcloud_username` is configured
3. User may need to re-login to get new token

### Issue: "User not found in database"

**Cause**: User exists in Keycloak but not in Supabase `users` table

**Solution**:
1. Run user sync flow: `nagen_supabase_users.yaml`
2. Or manually create user in Supabase:
```sql
INSERT INTO users (username, email, full_name, role)
VALUES ('rta_newuser', 'newuser@example.com', 'New User', 'ctv');
```

### Issue: "Invalid token signature"

**Cause**: JWT signature verification failed

**Possible Reasons**:
1. Token was tampered with
2. Wrong Keycloak public key (JWKS URL incorrect)
3. Token from different Keycloak realm

**Solution**:
1. Verify `KEYCLOAK_JWKS_URL` is correct
2. Check token issuer matches `KEYCLOAK_ISSUER`
3. User should re-login to get fresh token

### Issue: "Token expired"

**Cause**: JWT `exp` claim is in the past

**Solution**: User needs to re-login in rtwork app

## Security Considerations

### ✅ What This Function Does

1. **Validates JWT signature** with Keycloak public key (cryptographic proof)
2. **Checks token expiration** (time-bound access)
3. **Verifies issuer and audience** (prevents token misuse)
4. **Extracts verified identity** from JWT claims (not request body)
5. **Scopes database queries** to authenticated user only

### ✅ Why `##user.username##` in HTML is Safe

Even though users can inspect HTML and see usernames:
- Usernames are just display values (not used for auth)
- Backend validates JWT signature (can't be faked)
- Backend uses identity from JWT claims (not request body)
- Attackers can't impersonate users by knowing their username

**Analogy**: Seeing someone's name tag doesn't let you use their badge.

### ⚠️ Important Security Notes

1. **NEVER trust request body for identity**:
```typescript
// ❌ WRONG - User can fake this
const username = requestBody.username

// ✅ CORRECT - Extracted from validated JWT
const username = validatedClaims.rtcloud_username
```

2. **Service key must stay in Edge Function**:
- Never expose service key to client
- Never send service key in HTTP headers
- Edge Function uses it internally only

3. **JWT validation is critical**:
- Must verify signature (not just decode)
- Must check expiration
- Must validate issuer and audience

## Performance

### Expected Response Times

- **P50**: ~150ms (median)
- **P95**: ~400ms (95th percentile)
- **P99**: ~800ms (99th percentile)

### Optimization Tips

1. **Use indexes**: Ensure `users.username` and `transactions.user_id` are indexed
2. **Limit results**: Currently limited to 50 transactions, 12 monthly stats
3. **Add caching**: Consider caching in rtwork app (5 min TTL)
4. **Monitor JWKS**: JWKS endpoint is cached by `jose` library

## Changelog

### v1.0.0 (2026-01-12)
- Initial implementation
- Keycloak JWT validation
- Transaction and monthly stats retrieval
- CORS support for browser requests
- Comprehensive error handling

## Support

For issues or questions:
1. Check logs: `supabase functions logs dashboard-stats`
2. Review this README
3. Check Supabase Dashboard for function status
4. Verify environment variables are set correctly
