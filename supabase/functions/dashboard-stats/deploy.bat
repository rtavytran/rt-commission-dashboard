@echo off
REM RT Commission Dashboard - Edge Function Deployment Script (Windows)
REM This script deploys the dashboard-stats Edge Function to Supabase

setlocal enabledelayedexpansion

echo ======================================
echo RT Dashboard Edge Function Deployment
echo ======================================
echo.

REM Check if Supabase CLI is installed
supabase --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Supabase CLI is not installed
    echo Install it with: scoop install supabase
    echo Or visit: https://supabase.com/docs/guides/cli
    pause
    exit /b 1
)

echo [OK] Supabase CLI found
echo.

REM Check if logged in
supabase projects list >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Not logged in to Supabase
    echo Run: supabase login
    pause
    exit /b 1
)

echo [OK] Logged in to Supabase
echo.

REM Check if project is linked
if not exist ".supabase\config.toml" (
    echo [WARNING] Project not linked
    echo Linking to project pphoiqknkmwzstuokdmz...
    supabase link --project-ref pphoiqknkmwzstuokdmz
)

echo [OK] Project linked
echo.

REM Ask for confirmation
set /p "confirm=Deploy to production? (y/N): "
if /i not "%confirm%"=="y" (
    echo Deployment cancelled.
    pause
    exit /b 0
)

echo.
echo Deploying Edge Function...
echo.

REM Deploy the function
supabase functions deploy dashboard-stats

if errorlevel 1 (
    echo.
    echo [ERROR] Deployment failed!
    pause
    exit /b 1
)

echo.
echo [OK] Function deployed successfully!
echo.

REM Set environment variables
echo Configuring environment variables...
echo.

echo Setting KEYCLOAK_ISSUER...
supabase secrets set KEYCLOAK_ISSUER=https://accounts.rtworkspace.com/auth/realms/rta 2>nul

echo Setting KEYCLOAK_JWKS_URL...
supabase secrets set KEYCLOAK_JWKS_URL=https://accounts.rtworkspace.com/auth/realms/rta/protocol/openid-connect/certs 2>nul

echo.
echo [OK] Environment variables configured
echo.

REM Display function URL
set PROJECT_REF=pphoiqknkmwzstuokdmz
set FUNCTION_URL=https://%PROJECT_REF%.supabase.co/functions/v1/dashboard-stats

echo ======================================
echo Deployment Complete!
echo ======================================
echo.
echo Function URL:
echo %FUNCTION_URL%
echo.
echo Test with curl:
echo curl -X POST %FUNCTION_URL% ^
echo   -H "Authorization: Bearer <KEYCLOAK_JWT>" ^
echo   -H "Content-Type: application/json" ^
echo   -d "{}"
echo.
echo View logs:
echo supabase functions logs dashboard-stats --follow
echo.
echo Or in Supabase Dashboard:
echo https://supabase.com/dashboard/project/%PROJECT_REF%/functions/dashboard-stats/logs
echo.

pause
