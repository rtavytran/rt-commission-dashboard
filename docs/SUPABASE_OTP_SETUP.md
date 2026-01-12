# Configure Supabase to Send OTP Codes Instead of Magic Links

By default, Supabase sends magic links (clickable URLs) when you use `sign_in_with_otp()`. To send actual 6-digit OTP codes instead, you need to modify the email template.

**Reference:** [Supabase Email Passwordless Auth with OTP](https://supabase.com/docs/guides/auth/auth-email-passwordless#with-otp)

## How It Works

Supabase uses the **same "Magic Link" email template** for both magic links AND OTP codes. The key is to modify this template to display the `{{ .Token }}` variable, which contains the 6-digit OTP code.

## Configuration Steps

### Step 1: Access Email Templates

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project
3. Navigate to **Authentication** → **Email Templates**
4. Select **"Magic Link"** template

### Step 2: Modify the Email Subject and Template

When editing the Magic Link template, you'll see two fields:

#### Email Subject Line

The default subject is typically "Magic Link" or "Confirm your signup". Change it to something like:

```
Your One-Time Login Code
```

Or:

```
Your login code: {{ .Token }}
```

(Note: Including `{{ .Token }}` in the subject will show the actual 6-digit code in the email subject line)

#### Email Body Template

Edit the template body to include `{{ .Token }}`. Here's a recommended template:

```html
<h2>One-time login code</h2>
<p>Please enter this code to sign in:</p>
<h1 style="font-size: 48px; font-weight: bold; letter-spacing: 8px; margin: 20px 0;">{{ .Token }}</h1>
<p style="color: #666;">This code will expire in 60 minutes.</p>
<p style="color: #999; font-size: 12px;">If you didn't request this code, you can safely ignore this email.</p>
```

Or use a simpler text-based version:

```
Your one-time login code is:

{{ .Token }}

This code will expire in 60 minutes.

If you didn't request this code, you can safely ignore this email.
```

### Step 3: Configure OTP Expiration (Optional)

1. Navigate to **Authentication** → **Providers** → **Email**
2. Find **"Email OTP Expiration"** setting
3. Default: 3600 seconds (60 minutes)
4. Maximum: 86400 seconds (24 hours)
5. Note: Longer expiration times increase vulnerability to brute force attacks

### Step 4: Test the Configuration

1. In your app, click **"Send OTP"** on the login page
2. Check your email - you should now receive the 6-digit OTP code
3. Enter the code in the OTP field
4. Click **"Login with OTP"** to sign in

## Important Settings

### Default Behavior
- **Request frequency:** Users can request an OTP once every 60 seconds
- **Expiration:** OTPs expire after 60 minutes (3600 seconds) by default
- **Maximum expiry:** Cannot exceed 86400 seconds (1 day) to prevent brute force attacks
- **Configuration location:** Auth → Providers → Email → Email OTP Expiration

### Security Notes
- The longer an OTP remains valid, the greater the window for attackers to attempt brute force attacks
- Supabase enforces a maximum 24-hour expiration to maintain security
- Rate limiting prevents abuse (1 request per 60 seconds per email)

## Email Subject Line Options

You have several options for the email subject:

### Option 1: Generic Subject (Recommended)
```
Your One-Time Login Code
```
This keeps the subject clean and the code is only in the email body.

### Option 2: Include Code in Subject
```
Your login code: {{ .Token }}
```
This puts the 6-digit code directly in the subject line for quick access.

### Option 3: Dynamic Subject
```
{{ if .Token }}Your login code: {{ .Token }}{{ else }}Magic Link to Sign In{{ end }}
```
This shows different subjects based on whether it's an OTP or magic link.

## Supporting Both Magic Links and OTP Codes

You can include **both** the magic link and OTP code in the same email template:

**Subject:**
```
Sign in to RT Commission Dashboard
```

**Body:**

```html
<h2>Sign in to your account</h2>

<p><strong>Option 1:</strong> Click this magic link to sign in automatically:</p>
<p><a href="{{ .ConfirmationURL }}">Sign In</a></p>

<p><strong>Option 2:</strong> Or enter this code manually:</p>
<h1>{{ .Token }}</h1>

<p>This code expires in 60 minutes.</p>
```

This gives users flexibility to either click the link or manually enter the code.

## Current RT Commission Dashboard Behavior

The app currently supports:

- **Signup**: Password-based registration with email confirmation
- **Login**:
  - Password-based login
  - OTP-based login (sends code to email, user enters it manually)

After configuring the email template as described above, the OTP login will work with actual 6-digit codes that users can type in, rather than requiring them to click a magic link.
