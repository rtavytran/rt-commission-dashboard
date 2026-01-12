# rtwork App Integration Guide - OTP Authentication

## Overview

This guide explains how to integrate the RT Commission Dashboard into the rtwork app using **Supabase OTP authentication**.

### Why OTP Instead of Keycloak JWT?

- ✅ **No dependency** on rtwork developer's App.callApi whitelist
- ✅ **Simpler architecture** - no Keycloak integration needed
- ✅ **Built-in security** - Supabase handles JWT validation
- ✅ **User-friendly** - 6-digit OTP codes sent to email
- ✅ **Works everywhere** - mobile app, webapp, desktop

## Architecture Flow

```
┌─────────────────┐
│  rtwork App     │
│  (Mobile/Web)   │
└────────┬────────┘
         │
         │ 1. User enters email
         ▼
┌─────────────────┐
│  Login HTML     │
│  (in webview)   │
└────────┬────────┘
         │
         │ 2. Call Supabase.auth.signInWithOtp()
         ▼
┌─────────────────┐
│  Supabase Auth  │
│  (sends OTP)    │
└────────┬────────┘
         │
         │ 3. Email with 6-digit OTP
         ▼
┌─────────────────┐
│  User's Email   │
└────────┬────────┘
         │
         │ 4. User enters OTP
         ▼
┌─────────────────┐
│  Verify OTP     │
│  (get JWT)      │
└────────┬────────┘
         │
         │ 5. Store JWT in session
         ▼
┌─────────────────┐
│  Dashboard View │
│  (fetch data)   │
└────────┬────────┘
         │
         │ 6. Call Edge Function with JWT
         ▼
┌─────────────────┐
│  Edge Function  │
│  (validate JWT) │
└────────┬────────┘
         │
         │ 7. Return dashboard data
         ▼
┌─────────────────┐
│  Render Charts  │
│  & Stats        │
└─────────────────┘
```

## Implementation Steps

### Step 1: Create Login HTML Page

Create a file `dashboard-login.html` in your rtwork app:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Login</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .login-container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }

        p {
            color: #666;
            margin-bottom: 30px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 8px;
        }

        input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }

        input:focus {
            outline: none;
            border-color: #667eea;
        }

        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }

        button:active {
            transform: translateY(0);
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .message {
            padding: 12px 16px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 14px;
        }

        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .message.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }

        .hidden {
            display: none;
        }

        .otp-input {
            text-align: center;
            font-size: 24px;
            letter-spacing: 8px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Commission Dashboard</h1>
        <p>Sign in to view your dashboard</p>

        <div id="message" class="message hidden"></div>

        <!-- Email Step -->
        <div id="email-step">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input
                    type="email"
                    id="email"
                    placeholder="Enter your email"
                    autocomplete="email"
                    required
                >
            </div>
            <button id="send-otp-btn" onclick="sendOTP()">
                Send OTP Code
            </button>
        </div>

        <!-- OTP Step -->
        <div id="otp-step" class="hidden">
            <div class="form-group">
                <label for="otp">Enter OTP Code</label>
                <input
                    type="text"
                    id="otp"
                    placeholder="000000"
                    class="otp-input"
                    maxlength="6"
                    pattern="[0-9]{6}"
                    inputmode="numeric"
                    required
                >
            </div>
            <button id="verify-otp-btn" onclick="verifyOTP()">
                Verify & Login
            </button>
            <button
                style="margin-top: 10px; background: #6c757d;"
                onclick="backToEmail()">
                Back
            </button>
        </div>
    </div>

    <script>
        // Supabase Configuration
        const SUPABASE_URL = 'https://pphoiqknkmwzstuokdmz.supabase.co'
        const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY_HERE' // Get from Supabase Dashboard

        const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

        let userEmail = ''

        // Show message to user
        function showMessage(text, type = 'info') {
            const msgEl = document.getElementById('message')
            msgEl.textContent = text
            msgEl.className = `message ${type}`
            msgEl.classList.remove('hidden')

            if (type === 'success') {
                setTimeout(() => {
                    msgEl.classList.add('hidden')
                }, 5000)
            }
        }

        // Send OTP to user's email
        async function sendOTP() {
            const emailInput = document.getElementById('email')
            const email = emailInput.value.trim()

            if (!email) {
                showMessage('Please enter your email address', 'error')
                return
            }

            if (!email.includes('@')) {
                showMessage('Please enter a valid email address', 'error')
                return
            }

            const btn = document.getElementById('send-otp-btn')
            btn.disabled = true
            btn.textContent = 'Sending...'

            try {
                const { data, error } = await supabase.auth.signInWithOtp({
                    email: email,
                    options: {
                        shouldCreateUser: false // Only allow existing users
                    }
                })

                if (error) {
                    throw error
                }

                userEmail = email
                showMessage('OTP code sent to your email! Check your inbox.', 'success')

                // Switch to OTP input step
                document.getElementById('email-step').classList.add('hidden')
                document.getElementById('otp-step').classList.remove('hidden')

                // Focus on OTP input
                setTimeout(() => {
                    document.getElementById('otp').focus()
                }, 100)

            } catch (error) {
                console.error('Error sending OTP:', error)
                showMessage(error.message || 'Failed to send OTP. Please try again.', 'error')
            } finally {
                btn.disabled = false
                btn.textContent = 'Send OTP Code'
            }
        }

        // Verify OTP and login
        async function verifyOTP() {
            const otpInput = document.getElementById('otp')
            const otp = otpInput.value.trim()

            if (!otp || otp.length !== 6) {
                showMessage('Please enter the 6-digit OTP code', 'error')
                return
            }

            const btn = document.getElementById('verify-otp-btn')
            btn.disabled = true
            btn.textContent = 'Verifying...'

            try {
                const { data, error } = await supabase.auth.verifyOtp({
                    email: userEmail,
                    token: otp,
                    type: 'email'
                })

                if (error) {
                    throw error
                }

                if (!data.session) {
                    throw new Error('No session created')
                }

                showMessage('Login successful! Loading dashboard...', 'success')

                // Store session in localStorage
                localStorage.setItem('supabase_session', JSON.stringify(data.session))

                // Redirect to dashboard
                setTimeout(() => {
                    window.location.href = 'dashboard.html'
                }, 1000)

            } catch (error) {
                console.error('Error verifying OTP:', error)
                showMessage(error.message || 'Invalid OTP code. Please try again.', 'error')
            } finally {
                btn.disabled = false
                btn.textContent = 'Verify & Login'
            }
        }

        // Go back to email input
        function backToEmail() {
            document.getElementById('otp-step').classList.add('hidden')
            document.getElementById('email-step').classList.remove('hidden')
            document.getElementById('otp').value = ''
            document.getElementById('message').classList.add('hidden')
        }

        // Handle Enter key
        document.getElementById('email').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendOTP()
        })

        document.getElementById('otp').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') verifyOTP()
        })
    </script>
</body>
</html>
```

### Step 2: Create Dashboard HTML Page

Create a file `dashboard.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            padding: 24px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .stat-label {
            color: #666;
            font-size: 14px;
            margin-bottom: 8px;
        }

        .stat-value {
            color: #333;
            font-size: 32px;
            font-weight: 600;
        }

        .transactions {
            background: white;
            padding: 24px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }

        button {
            padding: 10px 20px;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 id="user-name">Loading...</h1>
                <p id="user-email" style="color: #666;"></p>
            </div>
            <button onclick="logout()">Logout</button>
        </div>

        <div id="loading" class="loading">
            Loading your dashboard...
        </div>

        <div id="dashboard" style="display: none;">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Sales</div>
                    <div class="stat-value" id="total-sales">₫0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Commission</div>
                    <div class="stat-value" id="total-commission">₫0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Transactions</div>
                    <div class="stat-value" id="transaction-count">0</div>
                </div>
            </div>

            <div class="transactions">
                <h2 style="margin-bottom: 20px;">Recent Transactions</h2>
                <div id="transactions-list"></div>
            </div>
        </div>
    </div>

    <script>
        // Supabase Configuration
        const SUPABASE_URL = 'https://pphoiqknkmwzstuokdmz.supabase.co'
        const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY_HERE'
        const EDGE_FUNCTION_URL = 'https://pphoiqknkmwzstuokdmz.supabase.co/functions/v1/dashboard-stats'

        const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

        // Check authentication and load dashboard
        async function init() {
            try {
                // Get session from localStorage
                const sessionData = localStorage.getItem('supabase_session')

                if (!sessionData) {
                    // Not logged in, redirect to login
                    window.location.href = 'dashboard-login.html'
                    return
                }

                const session = JSON.parse(sessionData)

                // Verify session is still valid
                const { data: { user }, error } = await supabase.auth.getUser(session.access_token)

                if (error || !user) {
                    // Session invalid, redirect to login
                    localStorage.removeItem('supabase_session')
                    window.location.href = 'dashboard-login.html'
                    return
                }

                // Load dashboard data
                await loadDashboard(session.access_token)

            } catch (error) {
                console.error('Init error:', error)
                window.location.href = 'dashboard-login.html'
            }
        }

        // Load dashboard data from Edge Function
        async function loadDashboard(accessToken) {
            try {
                const response = await fetch(EDGE_FUNCTION_URL, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: '{}'
                })

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
                }

                const data = await response.json()

                // Update UI with dashboard data
                document.getElementById('user-name').textContent = data.user.full_name || data.user.email
                document.getElementById('user-email').textContent = data.user.email

                document.getElementById('total-sales').textContent = formatCurrency(data.summary.total_sales)
                document.getElementById('total-commission').textContent = formatCurrency(data.summary.total_commissions)
                document.getElementById('transaction-count').textContent = data.summary.transaction_count

                // Render transactions
                renderTransactions(data.transactions)

                // Show dashboard, hide loading
                document.getElementById('loading').style.display = 'none'
                document.getElementById('dashboard').style.display = 'block'

            } catch (error) {
                console.error('Error loading dashboard:', error)
                alert('Failed to load dashboard: ' + error.message)
            }
        }

        // Format currency
        function formatCurrency(amount) {
            return new Intl.NumberFormat('vi-VN', {
                style: 'currency',
                currency: 'VND'
            }).format(amount)
        }

        // Render transactions list
        function renderTransactions(transactions) {
            const container = document.getElementById('transactions-list')

            if (!transactions || transactions.length === 0) {
                container.innerHTML = '<p style="color: #999;">No transactions yet</p>'
                return
            }

            container.innerHTML = transactions.map(tx => `
                <div style="padding: 16px; border-bottom: 1px solid #eee;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="font-weight: 500;">${tx.type}</span>
                        <span style="font-weight: 600;">${formatCurrency(tx.amount)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #999; font-size: 14px;">${new Date(tx.created_at).toLocaleDateString()}</span>
                        <span style="color: ${tx.status === 'approved' ? '#28a745' : '#ffc107'}; font-size: 14px;">${tx.status}</span>
                    </div>
                </div>
            `).join('')
        }

        // Logout
        async function logout() {
            await supabase.auth.signOut()
            localStorage.removeItem('supabase_session')
            window.location.href = 'dashboard-login.html'
        }

        // Initialize on page load
        init()
    </script>
</body>
</html>
```

### Step 3: Get Your Supabase Anon Key

1. Go to Supabase Dashboard: https://app.supabase.com
2. Select your project (pphoiqknkmwzstuokdmz)
3. Navigate to **Settings** → **API**
4. Copy the **anon/public** key
5. Replace `YOUR_SUPABASE_ANON_KEY_HERE` in both HTML files

### Step 4: Configure Supabase OTP Email Template

Follow the instructions in `SUPABASE_OTP_SETUP.md` to configure the email template to send 6-digit OTP codes.

### Step 5: Deploy Updated Edge Function

```bash
cd D:\RTA\GitHub\rt-commission-dashboard
supabase functions deploy dashboard-stats
```

### Step 6: Test the Flow

1. Open `dashboard-login.html` in rtwork app webview
2. Enter your email (must exist in Supabase `users` table)
3. Check email for 6-digit OTP code
4. Enter OTP code
5. Should redirect to `dashboard.html` with your data

## Security Notes

### ✅ What's Secure

1. **JWT Validation**: Supabase automatically validates JWT signature and expiration
2. **No Password Storage**: OTP is temporary and single-use
3. **Email Verification**: Only users with access to the email can login
4. **Session Expiration**: JWT tokens expire after 1 hour by default
5. **Data Scoping**: Edge Function only returns data for the authenticated user

### ⚠️ Important

1. **User Must Exist**: Set `shouldCreateUser: false` to prevent random signups
2. **Email Must Match**: User's email in Supabase Auth must match email in `users` table
3. **Keep Anon Key Public**: The anon key is meant to be public (used in frontend)
4. **Never Expose Service Key**: Only use service key in Edge Functions, never in frontend

## Troubleshooting

### Issue: "User not found in database"

**Cause**: User exists in Supabase Auth but not in `users` table

**Solution**: Ensure user exists in both places:
```sql
-- Check if user exists in users table
SELECT * FROM users WHERE email = 'user@example.com';

-- If not, create them
INSERT INTO users (email, full_name, role)
VALUES ('user@example.com', 'User Name', 'ctv');
```

### Issue: OTP email not received

**Cause**: Email template not configured or email provider issue

**Solution**:
1. Check Supabase Dashboard → Authentication → Email Templates
2. Ensure "Magic Link" template includes `{{ .Token }}`
3. Check spam folder
4. Verify email provider settings

### Issue: "Invalid or expired token"

**Cause**: JWT expired or session invalid

**Solution**: User needs to login again with new OTP

## Next Steps

1. ✅ Update Edge Function (done)
2. ✅ Create login/dashboard HTML pages (done)
3. ⏳ Get Supabase anon key from dashboard
4. ⏳ Replace `YOUR_SUPABASE_ANON_KEY_HERE` in HTML files
5. ⏳ Configure OTP email template in Supabase
6. ⏳ Deploy Edge Function
7. ⏳ Test login flow
8. ⏳ Integrate HTML pages into rtwork app

## Benefits Over Keycloak JWT Approach

| Aspect | Keycloak JWT | Supabase OTP |
|--------|--------------|--------------|
| **Dependency on rtwork** | High (needs whitelist) | None |
| **Complexity** | High (JWKS, validation) | Low (built-in) |
| **User Experience** | Seamless (auto-login) | One extra step (OTP) |
| **Security** | Strong | Strong |
| **Maintenance** | Manual JWT validation | Automatic |
| **Cost** | Same | Same |

The OTP approach trades a slightly longer login flow (enter email + OTP) for complete independence from rtwork's App.callApi whitelist and simpler architecture.
