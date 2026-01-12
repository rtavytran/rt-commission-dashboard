#!/bin/bash

# RT Commission Dashboard - Edge Function Deployment Script
# This script deploys the dashboard-stats Edge Function to Supabase

set -e  # Exit on error

echo "======================================"
echo "RT Dashboard Edge Function Deployment"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo -e "${RED}Error: Supabase CLI is not installed${NC}"
    echo "Install it with: brew install supabase/tap/supabase"
    echo "Or visit: https://supabase.com/docs/guides/cli"
    exit 1
fi

echo -e "${GREEN}✓ Supabase CLI found${NC}"

# Check if logged in
if ! supabase projects list &> /dev/null; then
    echo -e "${RED}Error: Not logged in to Supabase${NC}"
    echo "Run: supabase login"
    exit 1
fi

echo -e "${GREEN}✓ Logged in to Supabase${NC}"

# Check if project is linked
if [ ! -f ".supabase/config.toml" ]; then
    echo -e "${YELLOW}Warning: Project not linked${NC}"
    echo "Linking to project pphoiqknkmwzstuokdmz..."
    supabase link --project-ref pphoiqknkmwzstuokdmz
fi

echo -e "${GREEN}✓ Project linked${NC}"
echo ""

# Ask for confirmation
echo "This will deploy the dashboard-stats Edge Function to production."
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Deploying Edge Function..."
echo ""

# Deploy the function
supabase functions deploy dashboard-stats

echo ""
echo -e "${GREEN}✓ Function deployed successfully!${NC}"
echo ""

# Set environment variables (if not already set)
echo "Checking environment variables..."
echo ""

echo "Setting KEYCLOAK_ISSUER..."
supabase secrets set KEYCLOAK_ISSUER=https://accounts.rtworkspace.com/auth/realms/rta 2>&1 | grep -v "error" || true

echo "Setting KEYCLOAK_JWKS_URL..."
supabase secrets set KEYCLOAK_JWKS_URL=https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/certs 2>&1 | grep -v "error" || true

echo ""
echo -e "${GREEN}✓ Environment variables configured${NC}"
echo ""

# Display function URL
PROJECT_REF="pphoiqknkmwzstuokdmz"
FUNCTION_URL="https://${PROJECT_REF}.supabase.co/functions/v1/dashboard-stats"

echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
echo "Function URL:"
echo -e "${GREEN}${FUNCTION_URL}${NC}"
echo ""
echo "Test with:"
echo "curl -X POST ${FUNCTION_URL} \\"
echo "  -H \"Authorization: Bearer <KEYCLOAK_JWT>\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{}'"
echo ""
echo "View logs:"
echo "supabase functions logs dashboard-stats --follow"
echo ""
echo "Or in Supabase Dashboard:"
echo "https://supabase.com/dashboard/project/${PROJECT_REF}/functions/dashboard-stats/logs"
echo ""
