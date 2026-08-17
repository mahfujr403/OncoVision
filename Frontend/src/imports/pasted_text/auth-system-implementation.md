Phase 1 is complete.

Now continue with Phase 2.

Do not rewrite existing code.

Do not change architecture.

Only extend the project.

Maintain the same coding style and folder structure.


Continue building the existing OncoVision AI project.

IMPORTANT RULES

- Do NOT rewrite any existing code.
- Do NOT change the folder structure.
- Do NOT modify the architecture.
- Only extend the existing project.
- Reuse existing layouts, providers, hooks, types, constants, utilities, and reusable components.
- Follow the same coding style and naming conventions established in Phase 1.
- Write only production-ready code.

==================================================
Objective
==================================================

Implement a complete frontend authentication and authorization system.

This phase is ONLY about authentication, user management on the frontend, and role-based access.

No prediction features.

No dashboard analytics.

No medical functionality.

==================================================
Authentication Pages
==================================================

Complete the following pages:

- Login
- Register
- Forgot Password
- Reset Password
- Verify Email
- Change Password

Each page must:

- Use React Hook Form
- Use Zod validation
- Display inline validation errors
- Show loading states
- Show success/error toast notifications
- Have responsive layouts
- Match the premium design system created in Phase 1

==================================================
Authentication Flow
==================================================

Implement frontend-only authentication.

Do NOT connect to a backend.

Use mock API services.

Support:

- Login
- Register
- Logout
- Refresh Session
- Remember Me
- Auto Login (localStorage)
- Session Restore

==================================================
Roles
==================================================

Support three roles:

- ADMIN
- USER
- RESEARCHER

Create role utilities.

Role permissions must be reusable.

==================================================
Route Protection
==================================================

Implement complete route protection.

Guest

- Can access Landing
- Login
- Register

Authenticated User

- Can access Dashboard
- Prediction
- History
- Reports
- Settings

Researcher

- Everything User can access
- Plus Benchmark
- Plus Comparison

Admin

- Everything
- User Management
- Model Management
- Analytics
- Audit Logs
- System Health

Unauthorized users must be redirected gracefully.

==================================================
Navigation
==================================================

Sidebar and Navbar must change automatically depending on user role.

Example

Admin sees

Dashboard
Prediction
History
Reports
Users
Models
Analytics
Logs
System Health

User does not see admin pages.

==================================================
Profile
==================================================

Create Profile page.

Include

Profile Picture

Name

Email

Role

Organization

Joined Date

Edit Profile

Change Password

Logout

==================================================
Settings
==================================================

Create Settings UI.

Tabs

General

Appearance

Notifications

Security

Session

==================================================
User Menu
==================================================

Navbar dropdown should include

Profile

Settings

Theme

Logout

==================================================
Authentication Service
==================================================

Create reusable authentication service.

Methods

login()

register()

logout()

refreshSession()

changePassword()

forgotPassword()

verifyEmail()

Use mock implementations.

==================================================
Guards
==================================================

Improve

ProtectedRoute

PublicRoute

RoleRoute

AdminRoute

ResearcherRoute

Use reusable permission checking.

==================================================
Permission Utilities
==================================================

Create helper functions.

Examples

hasRole()

hasPermission()

canAccess()

isAdmin()

isResearcher()

==================================================
Loading & Error UX
==================================================

Create professional loading states.

Disable buttons while submitting.

Display skeletons where appropriate.

Show toast notifications.

Create reusable authentication error component.

==================================================
Accessibility
==================================================

Forms must support

Keyboard navigation

Focus management

ARIA labels

Accessible validation

==================================================
Code Quality
==================================================

Keep authentication completely isolated.

Use feature-based architecture.

Avoid duplicated logic.

Create reusable form components where possible.

==================================================
Deliverables
==================================================

Complete frontend authentication module.

Complete role-based authorization.

Complete navigation switching.

Complete protected routes.

Complete profile page.

Complete settings page.

Mock authentication only.

Stop after authentication is fully complete.

Wait for the next prompt before implementing AI prediction features.