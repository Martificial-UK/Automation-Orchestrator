# Automation Orchestrator - Frontend Dashboard

Professional web dashboard for the Automation Orchestrator platform, built with React, TypeScript, and Tailwind CSS.

## Features

- 🔐 **Secure Authentication** - JWT-based login with admin panel
- 📊 **Dashboard Overview** - Real-time metrics and system health
- 👥 **Lead Management** - Full CRUD operations for customer leads
- 📢 **Campaign Management** - View and manage marketing campaigns
- 🔄 **Workflow Automation** - Trigger and monitor automation workflows
- 📈 **Analytics** - Visual insights with charts and performance metrics
- ⚙️ **Settings** - User profile, API keys, and system configuration

## Tech Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Vite** - Lightning-fast build tool
- **Tailwind CSS** - Utility-first styling
- **React Router** - Client-side routing
- **Recharts** - Beautiful data visualization
- **Lucide React** - Modern icon library
- **Axios** - API communication

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

### 3. Build for Production

```bash
npm run build
```

This creates optimized static files in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── Layout.tsx     # Main dashboard layout with sidebar
│   │   └── ProtectedRoute.tsx  # Auth route guard
│   ├── contexts/          # React contexts
│   │   └── AuthContext.tsx     # Authentication state
│   ├── pages/             # Page components
│   │   ├── LoginPage.tsx       # Login screen
│   │   ├── DashboardPage.tsx   # Home dashboard
│   │   ├── LeadsPage.tsx       # Lead management
│   │   ├── CampaignsPage.tsx   # Campaign management
│   │   ├── WorkflowsPage.tsx   # Workflow automation
│   │   ├── AnalyticsPage.tsx   # Analytics & charts
│   │   └── SettingsPage.tsx    # Settings panel
│   ├── services/          # API services
│   │   └── api.ts         # API client & endpoints
│   ├── App.tsx            # Root component
│   ├── main.tsx           # Entry point
│   └── index.css          # Global styles
├── index.html             # HTML template
├── package.json           # Dependencies
├── vite.config.ts         # Vite configuration
├── tailwind.config.js     # Tailwind CSS config
└── tsconfig.json          # TypeScript config
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000` via proxy during development:

```typescript
// All API calls are proxied:
/api/* → http://localhost:8000/api/*
/health → http://localhost:8000/health
/metrics → http://localhost:8000/metrics
```

### Default Credentials

- **Username**: `admin`
- **Password**: `admin123`

## Available Scripts

- `npm run dev` - Start development server (hot reload)
- `npm run build` - Build production bundle
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint

## Deployment

### Option 1: Serve with FastAPI (Recommended)

The backend can serve the built frontend automatically:

1. Build the frontend:
   ```bash
   npm run build
   ```

2. Copy `dist/` contents to `backend/static/`

3. FastAPI will serve the dashboard at `http://localhost:8000/`

### Option 2: Static Hosting

Deploy the `dist/` folder to:
- **Netlify**: Drag & drop deployment
- **Vercel**: Connect GitHub repo
- **AWS S3 + CloudFront**: Static site hosting
- **Azure Static Web Apps**: GitHub Actions CI/CD

## Environment Configuration

Create `.env` file for custom configuration:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Browser Support

- Chrome/Edge (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)

## Development Tips

### Hot Reload

Vite provides instant hot module replacement. Save any file and see changes immediately.

### TypeScript

All API responses are typed for autocomplete and error checking:

```typescript
const { data } = await leadsAPI.getAll();
// data is typed as Lead[]
```

### Styling

Use Tailwind utility classes for consistent design:

```tsx
<button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700">
  Click Me
</button>
```

### API Calls

All API endpoints are centralized in `src/services/api.ts`:

```typescript
import { leadsAPI } from '@/services/api';

const leads = await leadsAPI.getAll();
const lead = await leadsAPI.create({ email: 'test@example.com' });
```

## Troubleshooting

**Port 3000 already in use?**
```bash
# Change port in vite.config.ts
server: { port: 3001 }
```

**API connection refused?**
- Ensure backend is running on port 8000
- Check CORS settings in FastAPI

**Build errors?**
```bash
rm -rf node_modules package-lock.json
npm install
```

## License

Proprietary - Automation Orchestrator Platform

---

**Ready for SME Market** ✅
- Professional UI/UX
- Responsive design (mobile-friendly)
- Secure authentication
- Full API integration
- Production-ready builds
