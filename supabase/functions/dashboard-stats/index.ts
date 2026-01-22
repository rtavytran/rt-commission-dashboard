/**
 * RT Commission Dashboard - Dashboard Stats Edge Function
 *
 * Purpose: Securely fetch dashboard data for rtwork mobile/web app users
 * Auth: Validates BOTH Keycloak JWT (OAuth2) and Supabase JWT (OTP)
 *
 * Environment Variables Required:
 * - SUPABASE_URL (auto-provided by Supabase)
 * - SUPABASE_ANON_KEY (auto-provided by Supabase)
 * - SUPABASE_SERVICE_ROLE_KEY (auto-provided by Supabase)
 * - KEYCLOAK_ISSUER (optional, for Keycloak JWT validation)
 * - KEYCLOAK_JWKS_URL (optional, for Keycloak JWT validation)
 */

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import * as jose from 'https://deno.land/x/jose@v4.11.1/index.ts'

// ==================== Configuration ====================

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')!
const SUPABASE_SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Keycloak configuration (optional - for OAuth2 support)
const KEYCLOAK_ISSUER = Deno.env.get('KEYCLOAK_ISSUER') || 'https://accounts.rtworkspace.com/auth/realms/rta'
const KEYCLOAK_JWKS_URL = Deno.env.get('KEYCLOAK_JWKS_URL') || `${KEYCLOAK_ISSUER}/protocol/openid-connect/certs`
const KEYCLOAK_AUDIENCES = (Deno.env.get('KEYCLOAK_AUDIENCES')
  ?.split(',')
  .map(s => s.trim())
  .filter(Boolean)) || ['dashboard-viewer', 'C155', 'account']
const CLOCK_TOLERANCE = 30 // seconds

// Create JWKS client for Keycloak JWT verification (lazy-loaded)
let KEYCLOAK_JWKS: any = null
function getKeycloakJWKS() {
  if (!KEYCLOAK_JWKS) {
    KEYCLOAK_JWKS = jose.createRemoteJWKSet(new URL(KEYCLOAK_JWKS_URL))
  }
  return KEYCLOAK_JWKS
}

// ==================== Types ====================

interface User {
  id: string
  username: string | null
  full_name: string | null
  email: string
  role: string
}

interface Transaction {
  id: string
  user_id: string
  amount: number
  type: string
  status: string
  shared_with_id?: string
  metadata?: any
  created_at: string
}

interface MonthlyStat {
  id: string
  user_id: string
  month: string
  personal_sales_volume: number
  shared_out_volume: number
  received_volume: number
  f1_sales_volume: number
  tier_rate: number
  comm_direct: number
  comm_shared: number
  comm_received: number
  comm_override: number
  total_commission: number
  last_updated: string
}

interface DashboardResponse {
  user: {
    id: string
    username: string | null
    full_name: string | null
    email: string
    role: string
  }
  target_user: {
    id: string
    username: string | null
    full_name: string | null
    email: string
    role: string
  }
  viewable_users: { id: string, label: string }[]
  summary: {
    total_sales: number
    total_commissions: number
    transaction_count: number
    current_month: MonthlyStat | null
  }
  transactions: Transaction[]
  monthly_stats: MonthlyStat[]
}

interface AuthResult {
  email: string
  username?: string
  method: 'keycloak' | 'supabase'
}

interface UserWithParent extends User {
  parent_id?: string | null
}

// ==================== Main Handler ====================

serve(async (req: Request) => {
  const startTime = Date.now()

  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return corsResponse(null, 204)
  }

  // Only allow POST requests
  if (req.method !== 'POST') {
    return corsResponse({ error: 'Method not allowed' }, 405)
  }

  try {
    // ===== STEP 1: Extract JWT from Authorization header =====
    const authHeader = req.headers.get('Authorization')

    if (!authHeader) {
      console.error('Missing Authorization header')
      return corsResponse({ error: 'Missing Authorization header' }, 401)
    }

    if (!authHeader.startsWith('Bearer ')) {
      console.error('Invalid Authorization format')
      return corsResponse({ error: 'Invalid Authorization format. Expected: Bearer <token>' }, 401)
    }

    const token = authHeader.replace('Bearer ', '')

    // ===== STEP 2: Validate JWT (try Keycloak first, then Supabase) =====
    const authResult = await validateToken(token)

    if (!authResult) {
      return corsResponse({ error: 'Invalid or expired token' }, 401)
    }

    console.log(`[${new Date().toISOString()}] Authenticated request - Email: ${authResult.email}, Method: ${authResult.method}`)

    // ===== STEP 3: Create service client for data queries =====
    const supabaseService = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
      auth: {
        autoRefreshToken: false,
        persistSession: false
      }
    })

    // ===== STEP 4: Look up user by email or username =====
    let user: User | null = null

    // If we have username from Keycloak, look up by username
    if (authResult.username) {
      const { data, error } = await supabaseService
        .from('users')
        .select('id, username, full_name, email, role')
        .eq('username', authResult.username)
        .single()

      if (!error && data) {
        user = data
      }
    }

    // If not found by username, try by email
    if (!user) {
      const { data, error } = await supabaseService
        .from('users')
        .select('id, username, full_name, email, role')
        .eq('email', authResult.email)
        .single()

      if (error) {
        console.error('User lookup error:', error)
        return corsResponse({ error: 'Failed to lookup user', details: error.message }, 500)
      }

      user = data
    }

    if (!user) {
      console.error(`User not found in database: ${authResult.email}`)
      return corsResponse({
        error: 'User not found in database',
        message: 'Your account may not be set up yet. Please contact support.',
        email: authResult.email
      }, 404)
    }

    console.log(`User found - ID: ${user.id}, Email: ${user.email}, Role: ${user.role}`)

    // ===== STEP 3.1: Determine target user (self or downline) =====
    const requestBody = await parseJsonBody(req)
    const { target_user_id: requestedTargetId } = requestBody || {}

    const downlineUsers = await fetchDownlineUsers(supabaseService, user.id)
    const viewableUsers = buildViewableUsers(user, downlineUsers)
    const allowedIds = new Set(viewableUsers.map(u => u.id))

    const targetUserId = (requestedTargetId && allowedIds.has(requestedTargetId))
      ? requestedTargetId
      : user.id

    const targetUser = targetUserId === user.id
      ? user
      : (downlineUsers.find(u => u.id === targetUserId) as UserWithParent | undefined)

    if (!targetUser) {
      return corsResponse({ error: 'Target user not found or not allowed' }, 403)
    }

    // ===== STEP 5: Fetch transactions =====
    const { data: transactions, error: txError } = await supabaseService
      .from('transactions')
      .select('id, user_id, amount, type, status, shared_with_id, metadata, created_at')
      .eq('user_id', targetUserId)
      .order('created_at', { ascending: false })
      .limit(50)

    if (txError) {
      console.error('Transaction query error:', txError)
      return corsResponse({ error: 'Failed to fetch transactions', details: txError.message }, 500)
    }

    // ===== STEP 6: Fetch monthly stats =====
    const { data: monthlyStats, error: statsError } = await supabaseService
      .from('monthly_stats')
      .select('*')
      .eq('user_id', targetUserId)
      .order('month', { ascending: false })
      .limit(12)

    if (statsError) {
      console.error('Monthly stats query error:', statsError)
      return corsResponse({ error: 'Failed to fetch monthly stats', details: statsError.message }, 500)
    }

    // ===== STEP 7: Calculate summary metrics =====
    const approvedTransactions = transactions?.filter(
      t => t.type === 'retail_sales' && t.status === 'approved'
    ) || []

    const totalSales = approvedTransactions.reduce((sum, t) => sum + (t.amount || 0), 0)

    const totalCommissions = monthlyStats?.reduce(
      (sum, s) => sum + (s.total_commission || 0),
      0
    ) || 0

    const currentMonthStat = monthlyStats?.[0] || null

    // ===== STEP 8: Build response =====
    const response: DashboardResponse = {
      user: {
        id: user.id,
        username: user.username,
        full_name: user.full_name,
        email: user.email,
        role: user.role
      },
      target_user: {
        id: targetUser.id,
        username: targetUser.username,
        full_name: targetUser.full_name,
        email: targetUser.email,
        role: targetUser.role,
      },
      viewable_users: viewableUsers,
      summary: {
        total_sales: totalSales,
        total_commissions: totalCommissions,
        transaction_count: transactions?.length || 0,
        current_month: currentMonthStat
      },
      transactions: transactions?.slice(0, 10) || [], // Return top 10 recent
      monthly_stats: monthlyStats || []
    }

    const elapsedTime = Date.now() - startTime
    console.log(`[${new Date().toISOString()}] Request completed - User: ${user.email}, Time: ${elapsedTime}ms`)

    return corsResponse(response, 200)

  } catch (error) {
    const elapsedTime = Date.now() - startTime
    console.error(`[${new Date().toISOString()}] Unexpected error (${elapsedTime}ms):`, error)

    return corsResponse({
      error: 'Internal server error',
      message: 'An unexpected error occurred. Please try again later.'
    }, 500)
  }
})

// ==================== Helper Functions ====================

/**
 * Validate token - tries Keycloak JWT first, then Supabase JWT
 */
async function validateToken(token: string): Promise<AuthResult | null> {
  // Try Keycloak JWT first (for OAuth2 flow)
  try {
    const keycloakResult = await validateKeycloakJWT(token)
    if (keycloakResult) {
      return keycloakResult
    }
  } catch (error) {
    console.log('Not a Keycloak JWT, trying Supabase:', error.message)
  }

  // Try Supabase JWT (for OTP flow)
  try {
    const supabaseResult = await validateSupabaseJWT(token)
    if (supabaseResult) {
      return supabaseResult
    }
  } catch (error) {
    console.log('Not a Supabase JWT:', error.message)
  }

  return null
}

/**
 * Validate Keycloak JWT (from OAuth2 flow)
 */
async function validateKeycloakJWT(token: string): Promise<AuthResult | null> {
  try {
    const JWKS = getKeycloakJWKS()

    // Verify JWT signature, expiration, issuer, audience
    const { payload: claims } = await jose.jwtVerify(token, JWKS, {
      issuer: KEYCLOAK_ISSUER,
      audience: KEYCLOAK_AUDIENCES,
      clockTolerance: CLOCK_TOLERANCE
    })

    // Extract identity from validated claims
    const username = claims.rtcloud_username as string
    const email = claims.email as string

    if (!email) {
      throw new Error('Missing email in Keycloak JWT')
    }

    return {
      email,
      username,
      method: 'keycloak'
    }
  } catch (error) {
    if (error instanceof jose.errors.JWTExpired) {
      throw new Error('Keycloak token expired')
    }
    if (error instanceof jose.errors.JWSSignatureVerificationFailed) {
      throw new Error('Invalid Keycloak token signature')
    }
    throw error
  }
}

/**
 * Validate Supabase JWT (from OTP flow)
 */
async function validateSupabaseJWT(token: string): Promise<AuthResult | null> {
  const supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: {
      headers: {
        Authorization: `Bearer ${token}`
      }
    },
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  })

  // Validate JWT with Supabase
  const { data: { user: authUser }, error: authError } = await supabaseClient.auth.getUser(token)

  if (authError) {
    throw new Error(`Supabase JWT validation failed: ${authError.message}`)
  }

  if (!authUser || !authUser.email) {
    throw new Error('Invalid Supabase JWT')
  }

  return {
    email: authUser.email,
    method: 'supabase'
  }
}

/**
 * Helper function to create CORS-enabled JSON responses
 */
function corsResponse(data: any, status: number): Response {
  return new Response(
    data ? JSON.stringify(data) : null,
    {
      status,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-Client-Info, apikey',
        'Access-Control-Max-Age': '86400', // 24 hours
      }
    }
  )
}

async function parseJsonBody(req: Request): Promise<any> {
  try {
    const body = await req.json()
    return body || {}
  } catch (_err) {
    return {}
  }
}

async function fetchDownlineUsers(supabaseService: any, rootUserId: string): Promise<UserWithParent[]> {
  const visited = new Set<string>([rootUserId])
  const results: UserWithParent[] = []
  let frontier: string[] = [rootUserId]
  const MAX_ITERATIONS = 10

  for (let depth = 0; depth < MAX_ITERATIONS && frontier.length > 0; depth++) {
    const { data, error } = await supabaseService
      .from('users')
      .select('id, username, full_name, email, role, parent_id')
      .in('parent_id', frontier)

    if (error) {
      console.error('Downline query error:', error)
      throw new Error(`Failed to fetch downline: ${error.message}`)
    }

    const next: string[] = []
    for (const u of data || []) {
      if (!visited.has(u.id)) {
        visited.add(u.id)
        results.push(u as UserWithParent)
        next.push(u.id)
      }
    }
    frontier = next
  }

  return results
}

function buildViewableUsers(self: UserWithParent, downline: UserWithParent[]): { id: string, label: string }[] {
  const formatLabel = (u: UserWithParent) => u.full_name || u.username || u.email || u.id
  const mapped = [
    { id: self.id, label: formatLabel(self) },
    ...downline.map(u => ({ id: u.id, label: formatLabel(u) }))
  ]
  // ensure uniqueness and stable order (self first, then downline)
  const seen = new Set<string>()
  return mapped.filter(u => {
    if (seen.has(u.id)) return false
    seen.add(u.id)
    return true
  })
}
