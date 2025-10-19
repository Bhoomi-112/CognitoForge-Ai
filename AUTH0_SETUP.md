# Auth0 Setup Guide for CognitoForge

This guide will help you set up Auth0 authentication for the CognitoForge frontend.

## Prerequisites

- An Auth0 account (sign up at https://auth0.com)
- Node.js and npm installed

## Step 1: Create an Auth0 Application

1. Log in to your [Auth0 Dashboard](https://manage.auth0.com/)
2. Navigate to **Applications** → **Applications**
3. Click **Create Application**
4. Choose:
   - **Name**: CognitoForge
   - **Type**: Single Page Application (SPA)
5. Click **Create**

## Step 2: Configure Application Settings

In your Auth0 application settings, configure the following:

### ⚠️ IMPORTANT: Configure These URLs in Auth0 Dashboard

**Your Auth0 Application:** `dev-gaytaln1ju54r4wq.us.auth0.com`

Navigate to: **Applications → Applications → CognitoForge → Settings**

### Allowed Callback URLs
```
http://localhost:3000,
http://localhost:3000/demo,
https://your-production-domain.com
```

### Allowed Logout URLs
```
http://localhost:3000,
https://your-production-domain.com
```

### Allowed Web Origins
```
http://localhost:3000,
https://your-production-domain.com
```

### Allowed Origins (CORS)
```
http://localhost:3000,
https://your-production-domain.com
```

**Important**: 
- Click **"Save Changes"** at the bottom after adding these URLs
- For production, replace `https://your-production-domain.com` with your actual domain

## Step 3: Set Up Environment Variables

✅ **Already configured!** Your `.env.local` file has been created with:

```bash
NEXT_PUBLIC_AUTH0_DOMAIN=dev-gaytaln1ju54r4wq.us.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=9fbUVdtuFO5hOIum5SMTPic1V4D22YqM
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Optional: API Audience

If you configured an Auth0 API, add this line to `.env.local`:
```bash
NEXT_PUBLIC_AUTH0_AUDIENCE=https://your-api-identifier
```

**Note:** The `.env.local` file is already in `.gitignore` and won't be committed to Git.

## Step 4: Install Dependencies

✅ **Already done!** Dependencies have been installed.

If you need to reinstall:
```bash
npm install
```

## Step 5: Test the Authentication

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Navigate to http://localhost:3000
3. You should see a **Sign In** button in the navbar
4. Click it to test the Auth0 login flow
5. After login, your profile picture and name should appear in the header

## Step 6: Protected Routes

The `/demo` page is automatically protected and will redirect unauthenticated users to the Auth0 login page.

## Features Implemented

✅ **Login/Logout**: Buttons in the navbar with loading states  
✅ **User Profile Display**: Shows user avatar and name after login  
✅ **Protected Routes**: `/demo` page requires authentication  
✅ **Loading States**: Smooth loading indicators during auth checks  
✅ **Redirect Handling**: Returns users to the intended page after login  

## Troubleshooting

### Issue: "Callback URL mismatch"
**Solution**: Make sure `http://localhost:3000` is in your Allowed Callback URLs in Auth0.

### Issue: "Invalid state"
**Solution**: Clear your browser cache and cookies, then try again.

### Issue: Environment variables not loading
**Solution**: 
1. Ensure `.env.local` exists in the root directory
2. Restart the Next.js dev server (`npm run dev`)
3. Make sure all variables start with `NEXT_PUBLIC_`

### Issue: Login button not working
**Solution**: Check the browser console for errors and verify your Auth0 credentials.

## Production Deployment

When deploying to production:

1. Update your Auth0 application settings with your production URLs
2. Set environment variables in your hosting platform (Vercel, Netlify, etc.)
3. Ensure HTTPS is enabled (required by Auth0)
4. Test the full authentication flow in production

## Security Best Practices

- ✅ Never commit `.env.local` to version control
- ✅ Use different Auth0 applications for development and production
- ✅ Regularly rotate Auth0 credentials
- ✅ Enable Multi-Factor Authentication (MFA) for admin users
- ✅ Monitor Auth0 logs for suspicious activity

## Additional Resources

- [Auth0 React SDK Documentation](https://auth0.com/docs/libraries/auth0-react)
- [Auth0 Dashboard](https://manage.auth0.com/)
- [Next.js Environment Variables](https://nextjs.org/docs/basic-features/environment-variables)
