## Request: Whitelist Supabase URL for `App.callApi` JWT Authentication

### What We Need
Add our Supabase project URL to the `App.callApi(includeToken=true)` allowlist:

**Specific URL**: `pphoiqknkmwzstuokdmz.supabase.co`
*(or `*.supabase.co` if wildcard is acceptable)*

### Why
We're migrating the commission dashboard to Supabase Edge Functions. The allowlist enables:
- **True SSO**: Keycloak JWT auto-attached to API calls, no separate login required
- **Seamless UX**: Users already authenticated in rtwork app, dashboard loads instantly
- **Secure**: Standard JWT validation at our Edge Function endpoint

### Current Blocker
Without the allowlist, we cannot use `App.callApi` with automatic JWT attachment, forcing us to implement OAuth2 redirect flows or OTP login (poor UX - users must authenticate twice).

### Impact
- Enables the simplest, most user-friendly authentication approach
- Zero additional development effort on rtwork side (just allowlist configuration)
- Maintains existing security model (Keycloak JWT validation)

### Alternative
If `*.supabase.co` is too broad, our specific project subdomain `pphoiqknkmwzstuokdmz.supabase.co` is sufficient.
