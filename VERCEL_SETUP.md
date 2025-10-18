# Vercel Deployment - Step-by-Step Fix

## 🔴 Current Issue
Your Vercel build is failing because it can't find the `dist` output directory.

**Error**: `No Output Directory named "dist" found after the Build completed`

## ✅ Solution: Configure Vercel Dashboard Settings

Follow these exact steps in your Vercel dashboard:

### Step 1: Go to Project Settings

1. Open your Vercel project
2. Click **"Settings"** tab at the top
3. Click **"General"** in the left sidebar

### Step 2: Configure Root Directory

Scroll down to **"Root Directory"** section:

- Click **"Edit"**
- Enter: `frontend`
- Click **"Save"**

This tells Vercel your app is in the `frontend` folder, not the root.

### Step 3: Configure Build & Output Settings

Scroll to **"Build & Development Settings"**:

Click **"Override"** and set:

| Setting | Value |
|---------|-------|
| **Framework Preset** | `Vite` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

Click **"Save"**

### Step 4: Add Environment Variables

1. Go to **"Settings"** → **"Environment Variables"**
2. Click **"Add New"**
3. Add:

| Name | Value | Environment |
|------|-------|-------------|
| `VITE_API_URL` | `https://your-backend-url.com` | Production, Preview, Development |

**Important**: Replace `your-backend-url.com` with your actual backend URL (see Step 5)

### Step 5: Deploy Your Backend First

**You MUST deploy the backend somewhere before the frontend will work!**

#### Option A: Render.com (Recommended - Free)

1. Go to https://render.com/
2. Sign in with GitHub
3. Click **"New +"** → **"Web Service"**
4. Connect your GitHub repository
5. Configure:
   - **Name**: `ctc-trading-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python api_server.py`
   - **Instance Type**: Free

6. Click **"Advanced"** and add Environment Variables:
   ```
   CTC_API_KEY = wxJM6xGFnLPodG5jLQUejTxRnL4SZog_3GS2_3h244Q
   CTC_API_URL = https://cornelltradingcompetition.org
   PORT = 10000
   ```

7. Click **"Create Web Service"**

8. **Copy your backend URL** (e.g., `https://ctc-trading-backend.onrender.com`)

9. Go back to Vercel and update the `VITE_API_URL` environment variable with this URL

#### Option B: Railway.app ($5/month but easier)

1. Go to https://railway.app/
2. Sign in with GitHub
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select your repository
5. Railway auto-detects Python
6. Add environment variables:
   ```
   CTC_API_KEY = wxJM6xGFnLPodG5jLQUejTxRnL4SZog_3GS2_3h244Q
   CTC_API_URL = https://cornelltradingcompetition.org
   ```
7. Copy the public URL Railway gives you
8. Update `VITE_API_URL` in Vercel with this URL

### Step 6: Redeploy on Vercel

1. Go to **"Deployments"** tab
2. Click the **"..."** menu on the latest deployment
3. Click **"Redeploy"**
4. Check **"Use existing Build Cache"** = NO
5. Click **"Redeploy"**

OR

1. Push a new commit to GitHub to trigger auto-deploy

---

## ✅ Checklist

Before redeploying, make sure:

- [ ] Root Directory set to `frontend`
- [ ] Build Command is `npm run build`
- [ ] Output Directory is `dist`
- [ ] Framework Preset is `Vite`
- [ ] Environment variable `VITE_API_URL` is set to your backend URL
- [ ] Backend is deployed and running (test at your-backend-url.com/api/health)
- [ ] Pushed the updated `vercel.json` to GitHub

---

## 🧪 Test Your Deployment

After deploying:

1. **Frontend Test**:
   - Visit your Vercel URL
   - Open browser console (F12)
   - Check for errors

2. **Backend Test**:
   - Visit: `https://your-backend-url.com/api/health`
   - Should return: `{"status": "ok", "message": "Trading bot API server is running"}`

3. **Integration Test**:
   - On your Vercel frontend, check if "Connection" shows green
   - Try clicking a strategy button
   - Check browser Network tab for API calls

---

## 🐛 Still Having Issues?

### Build still fails with "dist not found"
- Make sure Root Directory is `frontend` (not empty)
- Make sure Output Directory is `dist` (not `frontend/dist`)
- Clear build cache and redeploy

### Frontend deploys but shows "Cannot connect to server"
- Check that `VITE_API_URL` environment variable is set correctly
- Verify backend is running (visit backend URL directly)
- Check browser console for CORS errors

### Environment variables not working
- Make sure they're set for all environments (Production, Preview, Development)
- Redeploy after adding environment variables
- Use `import.meta.env.VITE_API_URL` in code (already done)

---

## 📝 Summary of Changes Made

I've updated your `vercel.json` to be minimal and let Vercel dashboard handle configuration:

```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

This is all you need! The rest is configured in Vercel dashboard.

---

## 🎯 Quick Commands

After configuring Vercel dashboard, commit the updated config:

```bash
git add vercel.json
git commit -m "Fix Vercel configuration for frontend deployment"
git push origin main
```

This will trigger a new deployment with the correct settings.

---

**Good luck! Your deployment should work now. 🚀**
