# Search Products Edge Function

Public endpoint for fuzzy product + variant search. No authentication required.

## Deploy

```bash
# Deploy with public access (no JWT verification)
supabase functions deploy search-products --no-verify-jwt
```

## Usage

```bash
curl -X POST "https://YOUR_PROJECT.supabase.co/functions/v1/search-products" \
  -H "Content-Type: application/json" \
  -d '{"search_term": "sungen wide"}'
```

## Response Format

```json
{
  "search_term": "sungen wide",
  "count": 3,
  "results": [
    {
      "product_id": "123456789",
      "product_name": "Tam lot ho tro vom ban chan SUNGEN",
      "variant_id": "987654321",
      "variant_title": "Wide 15",
      "concatenated_key": "product_id:123456789|variant_id:987654321"
    }
  ]
}
```

## Prerequisites

1. Create the `search_product_variants_fuzzy` function in Supabase:

```sql
CREATE OR REPLACE FUNCTION search_product_variants_fuzzy(search_term TEXT)
RETURNS TABLE (
    product_id TEXT,
    product_name TEXT,
    variant_id TEXT,
    variant_title TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id::TEXT AS product_id,
        p.title AS product_name,
        (v->>'id')::TEXT AS variant_id,
        COALESCE(v->>'title', 'Default') AS variant_title
    FROM products p
    CROSS JOIN LATERAL jsonb_array_elements(p.variants) AS v
    WHERE
        p.title ILIKE '%' || search_term || '%'
        OR
        similarity(p.title, search_term) > 0.3
        OR
        (v->>'title') ILIKE '%' || search_term || '%'
    ORDER BY
        similarity(p.title, search_term) DESC,
        p.title ASC,
        v->>'title' ASC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;
```

2. Ensure `pg_trgm` extension is enabled:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```
