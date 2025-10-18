CognitoForge — Static Prototype

What this is

This is a small static prototype for CognitoForge, an AI-driven red-team simulator for developers and CI/CD pipelines. It focuses on the UI, messaging, and basic accessibility improvements — not the backend AI engine.

Files

- `index.html` — main static page with CognitoForge messaging
- `styles.css` — responsive styling and accessibility focus helpers

How to open

You can open the prototype in two ways:

1) Open directly
   - Double-click `index.html` in the project root to open in your browser.

2) Serve with a simple static server (recommended for correct relative paths)

On Windows PowerShell, from the project root run:

```powershell
python -m http.server 8000; Start-Process "http://localhost:8000/"
```

Notes

- This visual prototype demonstrates the product concept and basic UX around adversarial testing. It does not include any security testing logic.
- If you'd like, I can convert this to a small React app, add accessibility tests, or wire a demo flow for an interactive simulation.
