# Backend Deployment Guide

## Option 1: Render.com (Recommended - Free Tier)

1. Push code to GitHub
2. Go to https://render.com → New + → Web Service
3. Connect your GitHub repo
4. Set:
   - **Root Directory**: `backend`
   - **Runtime**: `Docker`
   - **Plan**: Free
5. Add Environment Variables:
   - `MONGO_URI`: your MongoDB Atlas URI
   - `ADMIN_API_KEY`: random secret string (e.g. `my-super-secret-key-2026`)
6. Click Create Web Service

## Option 2: Railway.app (Free Tier)

1. Go to https://railway.app → New Project → Deploy from GitHub
2. Select your repo
3. Add service: `Docker`
4. Set Root Directory to `backend`
5. Add env vars: `MONGO_URI`, `ADMIN_API_KEY`
6. Deploy

## Option 3: Fly.io (Free Tier)

1. Install flyctl
2. `fly launch` in backend directory
3. `fly deploy`

## Option 4: VPS (Ubuntu)

```bash
# On your VPS
git clone <your-repo>
cd ecommerce-price-comparison/backend
docker build -t smart-shopping-backend .
docker run -d -p 8000:8000 \
  -e MONGO_URI="your-mongo-uri" \
  -e ADMIN_API_KEY="your-secret-key" \
  --restart unless-stopped \
  smart-shopping-backend
```

## After Deploy

Your backend will be available at `https://your-service.onrender.com` (or similar).

### GitHub Actions Setup

Add these secrets to your GitHub repo (Settings → Secrets and variables → Actions):

- `BACKEND_URL`: `https://your-service.onrender.com`
- `ADMIN_API_KEY`: same as your `ADMIN_API_KEY` env var

The workflow `.github/workflows/price-update.yml` will automatically run every 3 hours.

### Test Manually

```bash
curl -X POST https://your-service.onrender.com/api/admin/update-prices \
  -H "X-API-Key: your-secret-key"
```

### Check Stats

```bash
curl https://your-service.onrender.com/api/admin/price-stats \
  -H "X-API-Key: your-secret-key"
```
