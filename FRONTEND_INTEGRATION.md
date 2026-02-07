# Frontend Integration Instructions

## Quick Setup

### 1. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development (Frontend + Backend Together)

**Terminal 1 - Start Backend (API Server):**
```bash
cd "c:\AI Automation\Automation Orchestrator"
python -m uvicorn src.automation_orchestrator.wsgi:app --host 0.0.0.0 --port 8000 --workers 4
```

**Terminal 2 - Start Frontend (Development Server):**
```bash
cd frontend
npm run dev
```

- Frontend: http://localhost:3000 (with hot reload)
- Backend API: http://localhost:8000/api
- API Docs: http://localhost:8000/api/docs

### 3. Build for Production

**Build Frontend:**
```bash
cd frontend
npm run build
```

This creates production-ready files in `frontend/dist/`

**Start Integrated Server (Frontend + Backend):**
```bash
cd "c:\AI Automation\Automation Orchestrator"
python -m uvicorn src.automation_orchestrator.wsgi:app --host 0.0.0.0 --port 8000 --workers 4
```

Now visit http://localhost:8000 to see the full dashboard!

## What You Have Now

✅ **Professional Dashboard UI**
- Modern React + TypeScript frontend
- Responsive design (works on mobile/tablet/desktop)
- Professional UI/UX for SME customers

✅ **Complete Features**
- 🔐 Login page with authentication
- 📊 Dashboard with real-time metrics
- 👥 Lead management (create, read, update, delete)
- 📢 Campaign management view
- 🔄 Workflow automation panel
- 📈 Analytics with charts (Recharts)
- ⚙️ Settings page

✅ **Production-Ready Backend Integration**
- FastAPI serves both API and frontend
- Single deployment (no separate frontend server needed)
- CORS configured for development and production

## Architecture

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  User's Browser                                 │
│  http://localhost:8000                          │
│                                                 │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│                                                 │
│  FastAPI Backend (Port 8000)                    │
│                                                 │
│  ├── /            → React Frontend (SPA)        │
│  ├── /leads       → React Frontend (SPA)        │
│  ├── /campaigns   → React Frontend (SPA)        │
│  ├── /assets/*    → Static files (CSS/JS)       │
│  │                                               │
│  ├── /api/*       → REST API endpoints          │
│  ├── /health      → Health check                │
│  └── /metrics     → System metrics              │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Development Workflow

### Day-to-Day Development

1. **Backend changes:**
   - Edit files in `src/automation_orchestrator/`
   - Server auto-reloads (if using `--reload`)

2. **Frontend changes:**
   - Edit files in `frontend/src/`
   - Vite hot-reloads instantly (< 100ms)

3. **API changes:**
   - Update `src/automation_orchestrator/api.py`
   - Update `frontend/src/services/api.ts` if endpoints change

### Before Showing to Customers

```bash
# 1. Build frontend
cd frontend
npm run build

# 2. Start production server
cd ..
python -m uvicorn src.automation_orchestrator.wsgi:app --host 0.0.0.0 --port 8000 --workers 4
```

## Default Login

**Username:** admin  
**Password:** admin123

## Tech Stack

**Frontend:**
- React 18 (UI framework)
- TypeScript (type safety)
- Vite (build tool)
- Tailwind CSS (styling)
- React Router (navigation)
- Recharts (charts)
- Axios (API client)

**Backend:**
- FastAPI (REST API)
- Uvicorn (ASGI server)
- Pydantic (data validation)
- JWT authentication
- Redis queue (background tasks)

## Deployment Options

### Option 1: Single Server (Recommended)
Build frontend once, deploy FastAPI server - everything served from port 8000.

### Option 2: Separate Hosting
- Frontend: Netlify/Vercel/AWS S3
- Backend: Your server/cloud
- Configure CORS properly

### Option 3: Docker
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY frontend/dist /app/frontend/dist
COPY src /app/src
CMD ["uvicorn", "src.automation_orchestrator.wsgi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## Troubleshooting

**"Build frontend to access dashboard" message?**
```bash
cd frontend
npm install
npm run build
```

**Port 3000 already in use?**
```bash
# Edit frontend/vite.config.ts, change port to 3001
```

**API not connecting?**
- Ensure backend is running on port 8000
- Check CORS settings if accessing from different domain

**Build errors?**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## Next Steps for Market Launch

✅ **DONE - Major Items:**
- Professional UI/UX
- Full CRUD operations
- Authentication system
- Real-time metrics
- Responsive design

📋 **TODO - For SME Market:**
1. Add more visual polish (animations, loading states)
2. Create onboarding flow for new users
3. Add help/documentation links in UI
4. Create demo mode with sample data
5. Build marketing landing page
6. Add payment integration for license purchases
7. White-label options (custom branding)

**You now have a complete, sellable product for SMEs!** 🎉
