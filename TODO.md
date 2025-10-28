# TODO: Kasa Exporter Improvements

## Frontend Migration to @catalyst-ui

### Overview
Replace the current inline HTML/CSS/JS homepage with a proper React-based frontend using the `../catalyst-ui` component library.

### Goals
- Modern, responsive UI with component-based architecture
- Leverage existing Radix UI primitives and Tailwind CSS from catalyst-ui
- Better maintainability and extensibility
- Improved developer experience with hot module reloading
- Type-safe frontend with TypeScript

### Architecture Plan

#### 1. Project Structure
```
@kasa-exporter/
├── backend/                      # Python FastAPI backend (current kasa_exporter/)
│   ├── kasa_exporter/
│   │   ├── __main__.py          # API-only, no HTML rendering
│   │   ├── devices/
│   │   ├── routines/
│   │   └── utils/
│   └── pyproject.toml
├── frontend/                     # New React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx    # Main dashboard view
│   │   │   ├── DeviceCard.tsx   # Device display component
│   │   │   ├── TOUCalendar.tsx  # Time of Use calendar
│   │   │   └── SeasonToggle.tsx # Season toggle buttons
│   │   ├── hooks/
│   │   │   ├── useDevices.ts    # Fetch devices data
│   │   │   └── useTOUConfig.ts  # Fetch TOU configuration
│   │   ├── types/
│   │   │   └── index.ts         # TypeScript interfaces
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
└── docker-compose.yaml           # Updated to serve both backend + frontend
```

#### 2. Backend Changes (FastAPI)

**Current State:**
- `/` route returns HTML response with inline CSS/JS
- `/metrics` returns Prometheus metrics
- `/debug` returns debug info

**Target State:**
- `/` removed (frontend handles routing)
- `/api/devices` - GET endpoint returning JSON list of devices
- `/api/tou-config` - GET endpoint returning TOU configuration for all seasons
- `/api/health` - existing health check
- `/api/ready` - existing readiness check
- `/metrics` - unchanged
- `/debug` - unchanged

**New API Endpoints:**
```python
@app.get("/api/devices")
async def get_devices():
    return {
        "devices": device_registry.get_devices_info(),
        "total": len(device_registry.get_devices_info())
    }

@app.get("/api/tou-config")
async def get_tou_config():
    return {
        "current_season": calculator.get_current_season(),
        "summer": {...},
        "winter": {...}
    }
```

#### 3. Frontend Implementation (React + TypeScript)

**Components to Build:**

1. **Dashboard.tsx** - Main layout
   - Grid layout for stats (Total Devices, Online Now)
   - Device cards grid
   - TOU Calendar section
   - Links to Prometheus/Debug

2. **DeviceCard.tsx** - Individual device display
   - Use catalyst-ui Card component
   - Props: `{ alias, model, address, status }`
   - Green dot indicator for online status
   - Hover effects

3. **TOUCalendar.tsx** - Interactive calendar
   - 7-day weekly grid (Mon-Sun)
   - 24-hour rows
   - Color-coded cells (green/yellow/red)
   - Tooltips on hover showing rate and price
   - Current time highlighting
   - Props: `{ season: 'summer' | 'winter', config: TOUConfig }`

4. **SeasonToggle.tsx** - Season switcher
   - Toggle button group (Summer/Winter)
   - Use catalyst-ui Button component
   - Active state styling
   - Callback: `onSeasonChange(season: string)`

**Data Fetching with React Query:**
```typescript
// hooks/useDevices.ts
export function useDevices() {
  return useQuery({
    queryKey: ['devices'],
    queryFn: () => fetch('/api/devices').then(r => r.json()),
    refetchInterval: 10000 // auto-refresh every 10s
  })
}

// hooks/useTOUConfig.ts
export function useTOUConfig() {
  return useQuery({
    queryKey: ['tou-config'],
    queryFn: () => fetch('/api/tou-config').then(r => r.json())
  })
}
```

**TypeScript Types:**
```typescript
// types/index.ts
export interface Device {
  alias: string
  model: string
  address: string
  status: 'online' | 'offline'
}

export interface RatePeriod {
  super_off_peak: number
  off_peak: number
  on_peak: number
}

export interface SeasonConfig {
  rates: RatePeriod
  super_off_peak: [string, string][]
  off_peak: [string, string][]
  on_peak: [string, string][]
}

export interface TOUConfig {
  current_season: 'summer' | 'winter'
  summer: SeasonConfig
  winter: SeasonConfig
}
```

#### 4. Styling with catalyst-ui

**Import Components:**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from '@catalyst-ui/components'
import { Button } from '@catalyst-ui/components'
import { Badge } from '@catalyst-ui/components'
```

**Tailwind Classes:**
- Use existing utility classes from catalyst-ui
- Match current color scheme (purple/blue gradient background)
- Responsive grid layouts
- Consistent spacing and shadows

#### 5. Development Workflow

**Backend Development:**
```bash
cd workspace/@kasa-exporter
task dev  # Starts backend on :8000
```

**Frontend Development:**
```bash
cd workspace/@kasa-exporter/frontend
yarn dev  # Vite dev server on :5173, proxies /api to :8000
```

**Production Build:**
```bash
cd workspace/@kasa-exporter/frontend
yarn build  # Outputs to dist/
# Backend serves static files from dist/
```

#### 6. Docker Configuration

**Updated docker-compose.yaml:**
```yaml
services:
  kasa_exporter:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    # ... existing config

  kasa_frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3001:80"
    depends_on:
      - kasa_exporter
    environment:
      - VITE_API_URL=http://localhost:8000
```

**Or single container approach:**
- Build frontend → static files
- Backend serves static files with FastAPI StaticFiles
- Single Docker image with both backend and frontend

#### 7. Migration Steps

1. **Phase 1: API Endpoints**
   - [ ] Create `/api/devices` endpoint
   - [ ] Create `/api/tou-config` endpoint
   - [ ] Test API responses with curl/Postman
   - [ ] Keep existing `/` route for backwards compatibility

2. **Phase 2: Frontend Setup**
   - [ ] Create `frontend/` directory
   - [ ] Initialize Vite + React + TypeScript project
   - [ ] Install catalyst-ui as dependency
   - [ ] Set up Tailwind CSS configuration
   - [ ] Configure proxy to backend API

3. **Phase 3: Component Development**
   - [ ] Build Dashboard layout
   - [ ] Implement DeviceCard component
   - [ ] Port TOU Calendar to React component
   - [ ] Create SeasonToggle component
   - [ ] Add loading states and error handling

4. **Phase 4: Integration**
   - [ ] Connect components to API endpoints
   - [ ] Test auto-refresh behavior
   - [ ] Implement responsive design
   - [ ] Add accessibility features (ARIA labels, keyboard navigation)

5. **Phase 5: Production**
   - [ ] Configure FastAPI to serve static frontend build
   - [ ] Update Dockerfile to build frontend
   - [ ] Test production build
   - [ ] Remove old inline HTML from `__main__.py`
   - [ ] Update documentation

#### 8. Benefits

**Developer Experience:**
- Component reusability across projects
- Hot module reloading during development
- TypeScript type safety
- Better debugging with React DevTools

**User Experience:**
- Faster page loads with code splitting
- Smoother interactions (no page reloads)
- Better mobile responsiveness
- Consistent design system

**Maintainability:**
- Separation of concerns (backend/frontend)
- Easier to test components in isolation
- Can use Storybook from catalyst-ui for component development
- Reusable components across other projects

### Technical Considerations

**CORS Configuration:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Static File Serving (Production):**
```python
from fastapi.staticfiles import StaticFiles

# Serve frontend static files
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

**Environment Variables:**
```bash
# Frontend .env
VITE_API_URL=http://localhost:8000
VITE_REFRESH_INTERVAL=10000
```

### Open Questions

- [ ] Should we use React Query or SWR for data fetching?
- [ ] Do we need authentication/authorization for the dashboard?
- [ ] Should we add charts/graphs using D3.js (already in catalyst-ui)?
- [ ] WebSocket support for real-time device updates instead of polling?
- [ ] Dark mode support?

### Timeline Estimate

- **Phase 1 (API):** 2-4 hours
- **Phase 2 (Setup):** 2-3 hours
- **Phase 3 (Components):** 8-12 hours
- **Phase 4 (Integration):** 4-6 hours
- **Phase 5 (Production):** 2-4 hours

**Total:** ~18-29 hours of development time

### References

- catalyst-ui location: `workspace/catalyst-ui/`
- catalyst-ui Storybook: `yarn dev:storybook` (port 6006)
- FastAPI docs: https://fastapi.tiangolo.com/
- Vite docs: https://vitejs.dev/
- React Query: https://tanstack.com/query/latest
