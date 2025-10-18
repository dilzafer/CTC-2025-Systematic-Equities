# Deployment Guide - CTC Trading Bot

This guide covers deploying your trading bot to production.

## 🏗️ Architecture Overview

Your application has **two parts** that need separate deployment:
1. **Frontend** (React app) → Deploy to Vercel
2. **Backend** (Flask API) → Deploy to a server that supports long-running Python processes

## ⚠️ Important: Vercel Limitations

**Vercel is NOT ideal for the Flask backend** because:
- Vercel serverless functions have a **10-second execution timeout** (Hobby plan)
- Your trading strategies can run for minutes/hours
- Background threads are not supported in serverless

**Recommended approach**: Deploy frontend to Vercel, backend elsewhere.

---

## 📦 Option 1: Frontend on Vercel + Backend on Render/Railway (RECOMMENDED)

### Step 1: Deploy Backend to Render.com (Free Tier Available)

#### 1.1 Create `render.yaml`
Already created in your project root.

#### 1.2 Sign up at Render.com
1. Go to https://render.com
2. Sign in with GitHub
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Configure:
   - **Name**: `ctc-trading-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python api_server.py`
   - **Plan**: Free

#### 1.3 Set Environment Variables on Render
Add these in the Render dashboard:
```
CTC_API_URL=https://cornelltradingcompetition.org
CTC_API_KEY=wxJM6xGFnLPodG5jLQUejTxRnL4SZog_3GS2_3h244Q
PORT=10000
```

#### 1.4 Note Your Backend URL
After deployment, you'll get a URL like:
`https://ctc-trading-backend.onrender.com`

### Step 2: Deploy Frontend to Vercel

#### 2.1 Vercel Project Settings
1. Go to https://vercel.com
2. Import your GitHub repository
3. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

#### 2.2 Environment Variables on Vercel
Add in Vercel Dashboard → Settings → Environment Variables:

| Name | Value | Environment |
|------|-------|-------------|
| `VITE_API_URL` | `https://ctc-trading-backend.onrender.com` | Production |
| `VITE_API_URL` | `http://localhost:5001` | Development |

#### 2.3 Deploy
Click "Deploy" and Vercel will build and deploy your frontend.

---

## 📦 Option 2: Both on Railway.app (Easiest Full-Stack)

Railway supports both frontend and long-running backend processes.

### Step 1: Create `railway.toml`

Already created in your project root.

### Step 2: Deploy to Railway

1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will auto-detect both services

### Step 3: Configure Environment Variables

In Railway dashboard, set for **backend service**:
```
CTC_API_URL=https://cornelltradingcompetition.org
CTC_API_KEY=wxJM6xGFnLPodG5jLQUejTxRnL4SZog_3GS2_3h244Q
```

For **frontend service**:
```
VITE_API_URL=${{backend.RAILWAY_PUBLIC_URL}}
```

Railway will automatically link the services!

---

## 📦 Option 3: Frontend-Only on Vercel (Manual Backend)

If you want to run the backend on your own server/VPS:

### Step 1: Update Vercel Configuration

The `vercel.json` in your root is already configured.

### Step 2: Vercel Environment Variables

Add in Vercel Dashboard:
```
VITE_API_URL=https://your-backend-server.com
```

### Step 3: Deploy Backend to Your Server

SSH into your server and:
```bash
git clone your-repo
cd CTC-2025-Systematic-Equities
pip install -r requirements.txt
python api_server.py
```

Use a process manager like PM2 or systemd to keep it running.

---

## 🔐 Environment Variables Reference

### Backend Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CTC_API_URL` | Cornell Trading Competition API URL | No | `http://localhost:8000` |
| `CTC_API_KEY` | Your CTC API key | No | `DEFAULT_API_KEY` from code |
| `PORT` | Port for Flask server | No | `5000` |
| `DEBUG` | Enable debug mode | No | `false` |

### Frontend Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `VITE_API_URL` | Backend API server URL | No | `http://localhost:5001` |

---

## 🚀 Quick Deploy Steps for Vercel (Frontend Only)

### Via Vercel Dashboard:

1. **Import Project**
   - Go to https://vercel.com/new
   - Import your GitHub repo
   - Root Directory: `frontend`

2. **Configure Build**
   - Framework: Vite
   - Build Command: `npm run build`
   - Output: `dist`

3. **Environment Variables**
   ```
   VITE_API_URL = https://your-backend-url.com
   ```

4. **Deploy**
   - Click "Deploy"
   - Wait for build to complete

### Via Vercel CLI:

```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to frontend directory
cd frontend

# Deploy
vercel

# Follow prompts:
# - Link to existing project or create new
# - Set root directory: ./
# - Override settings: No
# - Add env variables when prompted
```

---

## 📝 Post-Deployment Checklist

### Backend Deployed ✓
- [ ] Backend URL is accessible (test `/api/health`)
- [ ] Environment variables are set correctly
- [ ] CORS is enabled (flask-cors installed)
- [ ] API key is configured
- [ ] Server stays running (use PM2/systemd)

### Frontend Deployed ✓
- [ ] Frontend URL loads correctly
- [ ] `VITE_API_URL` points to backend
- [ ] Connection status shows "Connected"
- [ ] Can fetch positions (check browser console)
- [ ] Buttons work without errors

### Integration ✓
- [ ] Frontend can reach backend API
- [ ] No CORS errors in browser console
- [ ] Positions update in real-time
- [ ] Strategies execute successfully

---

## 🐛 Troubleshooting

### "Cannot connect to server"
- Check `VITE_API_URL` in Vercel environment variables
- Verify backend is running (visit backend URL directly)
- Check CORS headers in backend response

### "Strategies not starting"
- Check backend logs for errors
- Verify API key is set in backend env vars
- Test backend endpoint with curl:
  ```bash
  curl -X POST https://your-backend/api/strategy/ultra-long-aaa
  ```

### "Build failed on Vercel"
- Check build logs in Vercel dashboard
- Verify `package.json` is in frontend directory
- Ensure all dependencies are listed

### Backend times out after 10 seconds (Vercel Serverless)
- **This is expected!** Vercel serverless is not suitable for long-running tasks
- Solution: Deploy backend to Render, Railway, or your own server

---

## 🎯 Recommended Deployment Strategy

For the **Cornell Trading Competition**:

**Option A: Development/Testing**
- Frontend: Localhost (npm run dev)
- Backend: Localhost (python api_server.py)
- Fast iteration, easy debugging

**Option B: Competition Day (Simple)**
- Frontend: Vercel (free, fast CDN)
- Backend: Railway (free tier, supports long-running processes)
- Total cost: $0, easy setup

**Option C: Competition Day (Advanced)**
- Frontend: Vercel
- Backend: Your VPS/server with reliable uptime
- More control, need server management skills

---

## 📞 Support

If you encounter deployment issues:
1. Check Vercel build logs
2. Check backend server logs
3. Test API endpoints with curl/Postman
4. Verify environment variables are set correctly

---

## 🔗 Useful Links

- **Vercel Docs**: https://vercel.com/docs
- **Render Docs**: https://render.com/docs
- **Railway Docs**: https://docs.railway.app
- **Vite Env Variables**: https://vitejs.dev/guide/env-and-mode.html

---

**Good luck with your deployment! 🚀**
