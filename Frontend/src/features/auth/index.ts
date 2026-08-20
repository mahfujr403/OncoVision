export { authService } from './services/authService';
export { AuthErrorAlert } from './components/AuthErrorAlert';
export { PasswordStrength } from './components/PasswordStrength';
export { AuthDivider } from './components/AuthDivider';
export { usePasswordToggle } from './hooks/usePasswordToggle';
// DemoCredentials intentionally not exported: it offered one-click login
// for admin/researcher/doctor accounts that only ever existed in the mock
// auth layer. The real backend has no seeded accounts and only two roles
// (admin/user), so autofilling those credentials would just produce a
// real 401. Component file left in place rather than deleted, per project
// rule against deleting without cause — it's simply unused now.
