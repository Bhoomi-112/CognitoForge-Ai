# 🛡️ CognitoForge - AI Red Team Testing PlatformCognitoForge — Static Prototype



A modern Next.js application with Auth0 authentication for AI-powered security testing.What this is



## 📁 Project StructureThis is a small static prototype for CognitoForge, an AI-driven red-team simulator for developers and CI/CD pipelines. It focuses on the UI, messaging, and basic accessibility improvements — not the backend AI engine.



```Files

c:\workspace\prototype\

├── src/                          # Source code- `index.html` — main static page with CognitoForge messaging

│   ├── app/                      # Next.js App Router- `styles.css` — responsive styling and accessibility focus helpers

│   │   ├── api/auth/[...auth0]/  # Auth0 API routes

│   │   ├── demo/                 # Protected demo pageHow to open

│   │   ├── layout.tsx            # Root layout

│   │   └── page.tsx              # Home pageYou can open the prototype in two ways:

│   ├── components/               # React components

│   │   ├── auth/                 # Authentication components1) Open directly

│   │   ├── layout/               # Layout components (Header, Footer)   - Double-click `index.html` in the project root to open in your browser.

│   │   ├── features/             # Feature-specific components

│   │   └── ui/                   # Reusable UI components2) Serve with a simple static server (recommended for correct relative paths)

│   ├── lib/                      # Utilities and configurations

│   ├── styles/                   # Global stylesOn Windows PowerShell, from the project root run:

│   ├── types/                    # TypeScript type definitions

│   └── hooks/                    # Custom React hooks```powershell

├── public/                       # Static assetspython -m http.server 8000; Start-Process "http://localhost:8000/"

├── docs/                         # Documentation```

├── .env.local.example           # Environment variables template

├── package.json                 # DependenciesNotes

├── tailwind.config.js          # Tailwind CSS configuration

├── tsconfig.json               # TypeScript configuration- This visual prototype demonstrates the product concept and basic UX around adversarial testing. It does not include any security testing logic.

└── next.config.js              # Next.js configuration- If you'd like, I can convert this to a small React app, add accessibility tests, or wire a demo flow for an interactive simulation.

```

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Setup Environment**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your Auth0 credentials
   ```

3. **Run Development Server**
   ```bash
   npm run dev
   ```

4. **Open Application**
   ```
   http://localhost:3000
   ```

## 🔧 Technologies Used

- **Frontend**: Next.js 14, React 18, TypeScript
- **Styling**: TailwindCSS, shadcn/ui components
- **Authentication**: Auth0
- **Animations**: Framer Motion
- **Icons**: Lucide React

## 📖 Documentation

See the `docs/` folder for detailed setup guides:
- `docs/SETUP.md` - Complete setup instructions
- `docs/AUTH0_SETUP.md` - Auth0 configuration guide

## 🏗️ Development

### Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

### Component Organization

- **UI Components** (`src/components/ui/`) - Reusable, styled components
- **Layout Components** (`src/components/layout/`) - Header, Footer, etc.
- **Auth Components** (`src/components/auth/`) - Authentication-related components
- **Feature Components** (`src/components/features/`) - Business logic components

## 🔒 Security Features

- ✅ Auth0 authentication
- ✅ Protected routes
- ✅ User session management
- ✅ Social login support
- ✅ Secure token handling

## 🎨 UI Features

- ✅ Dark theme with purple accents
- ✅ Glass morphism effects
- ✅ Responsive design
- ✅ Smooth animations
- ✅ Modern typography

---

Built with ❤️ for secure development workflows.