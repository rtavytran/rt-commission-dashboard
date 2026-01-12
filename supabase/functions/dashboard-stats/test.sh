#!/bin/bash

# RT Commission Dashboard - Edge Function Test Script
# This script helps test the dashboard-stats Edge Function

set -e

echo "======================================"
echo "RT Dashboard Edge Function Test"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_REF="pphoiqknkmwzstuokdmz"
LOCAL_URL="http://localhost:54321/functions/v1/dashboard-stats"
PROD_URL="https://${PROJECT_REF}.supabase.co/functions/v1/dashboard-stats"

# Menu
echo "Select environment:"
echo "1) Local (http://localhost:54321)"
echo "2) Production (https://${PROJECT_REF}.supabase.co)"
echo ""
read -p "Choice (1-2): " env_choice

case $env_choice in
    1)
        FUNCTION_URL=$LOCAL_URL
        echo -e "${BLUE}Testing LOCAL environment${NC}"
        echo ""
        echo "Make sure local Supabase is running:"
        echo "  supabase start"
        echo "  supabase functions serve dashboard-stats"
        echo ""
        ;;
    2)
        FUNCTION_URL=$PROD_URL
        echo -e "${YELLOW}Testing PRODUCTION environment${NC}"
        echo ""
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

# Get JWT token
echo "You need a valid Keycloak JWT token."
echo ""
echo "To get one:"
echo "1. Login to rtwork app (mobile or web)"
echo "2. Open browser DevTools (F12)"
echo "3. Go to Network tab"
echo "4. Trigger an API call"
echo "5. Find the request, copy Authorization header value"
echo ""
read -p "Paste JWT token (or press Enter to use test token): " jwt_token

if [ -z "$jwt_token" ]; then
    echo -e "${YELLOW}Using test token (will likely fail with 401)${NC}"
    jwt_token="test-token-will-fail"
fi

# Clean up token if it has "Bearer " prefix
jwt_token=${jwt_token#"Bearer "}
jwt_token=${jwt_token#"bearer "}

echo ""
echo -e "${BLUE}Making request...${NC}"
echo ""

# Make request
response=$(curl -X POST "$FUNCTION_URL" \
    -H "Authorization: Bearer $jwt_token" \
    -H "Content-Type: application/json" \
    -d '{}' \
    -w "\n%{http_code}" \
    -s)

# Split response and status code
http_code=$(echo "$response" | tail -n1)
response_body=$(echo "$response" | sed '$d')

echo "======================================"
echo "Response"
echo "======================================"
echo ""
echo -e "${BLUE}Status Code:${NC} $http_code"
echo ""

# Check status code
if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ SUCCESS${NC}"
    echo ""
    echo "Response body:"
    echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
elif [ "$http_code" = "401" ]; then
    echo -e "${RED}✗ UNAUTHORIZED${NC}"
    echo ""
    echo "Possible reasons:"
    echo "- Invalid JWT token"
    echo "- Expired JWT token"
    echo "- Wrong JWT issuer"
    echo ""
    echo "Response:"
    echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
elif [ "$http_code" = "404" ]; then
    echo -e "${YELLOW}✗ USER NOT FOUND${NC}"
    echo ""
    echo "User exists in Keycloak but not in Supabase database."
    echo "Run user sync flow to add them."
    echo ""
    echo "Response:"
    echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
elif [ "$http_code" = "500" ]; then
    echo -e "${RED}✗ SERVER ERROR${NC}"
    echo ""
    echo "Something went wrong on the server."
    echo "Check logs: supabase functions logs dashboard-stats"
    echo ""
    echo "Response:"
    echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
else
    echo -e "${RED}✗ ERROR${NC}"
    echo ""
    echo "Response:"
    echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
fi

echo ""
echo "======================================"
echo ""

# Offer to check logs
if [ "$env_choice" = "1" ]; then
    read -p "View local logs? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        supabase functions logs dashboard-stats --follow
    fi
elif [ "$env_choice" = "2" ]; then
    echo "View production logs:"
    echo "  supabase functions logs dashboard-stats --follow"
    echo ""
    echo "Or in Supabase Dashboard:"
    echo "  https://supabase.com/dashboard/project/${PROJECT_REF}/functions/dashboard-stats/logs"
    echo ""
fi
