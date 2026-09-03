export { authService } from './services/authService';
export { AuthErrorAlert } from './components/AuthErrorAlert';
export { PasswordStrength } from './components/PasswordStrength';
export { AuthDivider } from './components/AuthDivider';
export { usePasswordToggle } from './hooks/usePasswordToggle';
// DemoCredentials: one-click autofill for the two seeded demo accounts
// (admin/user) created by `backend/scripts/seed_demo_users.py`. Re-enabled
// now that a real seed script exists — see that script for how these
// accounts get into the database. Keep DEMO_CREDENTIALS below in sync with
// the script if either changes.
export { DemoCredentials } from './components/DemoCredentials';
