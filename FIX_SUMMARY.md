# Fix Summary: Nagen Transaction Sync - UUID Empty String Error & Key Name Update

## Problem 1: UUID Empty String Error
The Kestra workflow `nagen_supabase_transactions_v2_test.yaml` was failing with the following error:

```
ERROR: Supabase upsert failed: 400 - {"code":"22P02","details":null,"hint":null,"message":"invalid input syntax for type uuid: \"\""}
```

## Root Cause
When processing Shopify orders without an affiliate reference (`rt_aff_ref`), the code was setting UUID fields to empty strings (`""`) instead of `None` (null):

```python
row = {
    ...
    "shared_with_id": "",      # ❌ Empty string causes PostgreSQL error
    "reference_id": "",        # ❌ Empty string causes PostgreSQL error
}
```

PostgreSQL/Supabase expects UUID columns to contain either:
- A valid UUID string (e.g., `"1b35a0c1-ab2f-439e-b97f-44a36c8f1be7"`)
- `NULL` (represented as `None` in Python)

Empty strings (`""`) are **not valid** for UUID columns and cause a type conversion error.

## Solution 1: Fixed UUID Fields
Changed empty strings to `None` in the `parse_shopify_order` function (around line 268-270):

```python
row = {
    ...
    "shared_with_id": None,    # ✅ Correct: None converts to NULL in PostgreSQL
    "reference_id": None,      # ✅ Correct: None converts to NULL in PostgreSQL
}
```

---

## Problem 2: Inconsistent Key Name for Affiliate Reference

The code was looking for two different key names:
- `"rt_aff_ref"` in `note_attributes` (cart checkout)
- `"_rt_aff_ref"` in `line_items.properties` (Buy it now)

This inconsistency meant cart checkout orders wouldn't be properly tracked.

## Solution 2: Standardized Key Name

Updated the code to use `"_rt_aff_ref"` (with underscore prefix) in **both** locations:

### Changes in `extract_rt_aff_ref` function:
```python
# Before:
if attr.get("name") == "rt_aff_ref":  # ❌ Missing underscore

# After:
if attr.get("name") == "_rt_aff_ref":  # ✅ Consistent with line_items
```

### Changes in ref_source detection:
```python
# Before:
if attr.get("name") == "rt_aff_ref" and attr.get("value") == rt_aff_ref:  # ❌

# After:
if attr.get("name") == "_rt_aff_ref" and attr.get("value") == rt_aff_ref:  # ✅
```

### Updated documentation in function docstring:
```python
"""Extract rt_aff_ref value from Shopify order.

Checks two locations:
1. note_attributes[name="_rt_aff_ref"] - for cart checkout       # ✅ Updated
2. line_items[].properties[name="_rt_aff_ref"] - for "Buy it now" orders
"""
```

---

## Files Modified
- `D:\RTA\rta-flow\_flows\flowai\nagen_transaction_sync\flow\nagen_supabase_transactions_v2_test.yaml`

## Testing Recommendation
Test the fix with Shopify orders in different scenarios:

### Scenario 1: Cart Checkout with Affiliate
- ✅ Has `_rt_aff_ref` in `note_attributes`
- ✅ `financial_status` = "paid" or "pending"
- Expected: User looked up from `_rt_aff_ref` value

### Scenario 2: Buy It Now with Affiliate
- ✅ Has `_rt_aff_ref` in `line_items[].properties`
- ✅ `financial_status` = "paid" or "pending"
- Expected: User looked up from `_rt_aff_ref` value

### Scenario 3: Anonymous Order (No Affiliate)
- ✅ No `_rt_aff_ref` in either location
- ✅ `financial_status` = "paid" or "pending"
- Expected: 
  - `user_id` = `1b35a0c1-ab2f-439e-b97f-44a36c8f1be7` (shopify_anonymous)
  - `shared_with_id` = `NULL`
  - `reference_id` = `NULL`
  - `metadata.anonymous_order` = `true`

## Additional Context
The workflow handles two types of orders:
1. **RTWork orders**: Have `user_id` as username, may have `shared_with_id` and `reference_id`
2. **Shopify orders**: Extract user from `_rt_aff_ref`, fallback to anonymous user

For Shopify orders:
- The system now consistently looks for `_rt_aff_ref` in both cart and Buy It Now flows
- Without affiliate tracking, uses the `shopify_anonymous` user UUID
- Sets optional UUID fields to `NULL` (not empty strings)
- Logs tracking information in metadata (ref_source, anonymous_order, etc.)
