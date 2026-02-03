/**
 * Search Products Edge Function
 *
 * Purpose: Public endpoint for fuzzy product + variant search
 * Auth: None required (--no-verify-jwt)
 *
 * Environment Variables Required:
 * - SUPABASE_URL (auto-provided by Supabase)
 * - SUPABASE_SERVICE_ROLE_KEY (auto-provided by Supabase)
 */

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// ==================== Configuration ====================

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// ==================== Types ====================

interface ProductVariantResult {
  product_id: string
  product_name: string
  variant_id: string
  variant_title: string
  concatenated_key: string
}

interface SearchRequest {
  search_term: string
}

// ==================== Main Handler ====================

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return corsResponse(null, 204)
  }

  // Only allow POST requests
  if (req.method !== 'POST') {
    return corsResponse({ error: 'Method not allowed. Use POST.' }, 405)
  }

  try {
    // ===== STEP 1: Parse request body =====
    const body = await parseJsonBody(req) as SearchRequest

    if (!body.search_term || typeof body.search_term !== 'string') {
      return corsResponse({
        error: 'Missing or invalid search_term',
        usage: { search_term: 'string (required)' }
      }, 400)
    }

    const searchTerm = body.search_term.trim()

    if (searchTerm.length < 1) {
      return corsResponse({ error: 'search_term cannot be empty' }, 400)
    }

    // ===== STEP 2: Create Supabase client =====
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
      auth: {
        autoRefreshToken: false,
        persistSession: false
      }
    })

    // ===== STEP 3: Call the RPC function =====
    const { data, error } = await supabase.rpc('search_product_variants_fuzzy', {
      search_term: searchTerm
    })

    if (error) {
      console.error('RPC error:', error)
      return corsResponse({
        error: 'Database query failed',
        details: error.message
      }, 500)
    }

    // ===== STEP 4: Add concatenated_key to each result =====
    const results: ProductVariantResult[] = (data || []).map((row: any) => ({
      product_id: row.product_id,
      product_name: row.product_name,
      variant_id: row.variant_id,
      variant_title: row.variant_title,
      concatenated_key: `product_id:${row.product_id}|variant_id:${row.variant_id}`
    }))

    // ===== STEP 5: Return response =====
    return corsResponse({
      search_term: searchTerm,
      count: results.length,
      results
    }, 200)

  } catch (error) {
    console.error('Unexpected error:', error)
    return corsResponse({
      error: 'Internal server error',
      message: 'An unexpected error occurred. Please try again.'
    }, 500)
  }
})

// ==================== Helper Functions ====================

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
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400', // 24 hours
      }
    }
  )
}

/**
 * Safely parse JSON body
 */
async function parseJsonBody(req: Request): Promise<any> {
  try {
    return await req.json()
  } catch (_err) {
    return {}
  }
}
