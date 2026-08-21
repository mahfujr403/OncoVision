Design Phase 1 of "OncoVision AI" — an enterprise-oriented AI-assisted histopathology image classification platform focused on Lung and Colon Cancer image analysis.

This is a professional AI/ML engineering showcase project. The platform is currently under development.

IMPORTANT:
Never imply clinical validation, medical diagnosis certainty, FDA approval, regulatory approval, or production clinical readiness.

Use language such as:

* AI-assisted analysis
* AI Prediction
* Model Confidence
* Analysis Result

Do NOT use:

* Diagnosis confirmed
* Clinically validated
* Medical diagnosis
* Guaranteed accuracy

# PHASE 1 SCOPE

Design ONLY the structural and visual foundation of the application.

Create:

1. Login screen
2. Register screen
3. Authenticated application shell
4. Responsive sidebar navigation
5. Top navigation bar
6. Dashboard structural skeleton
7. Reusable loading states
8. Reusable empty states
9. Reusable error states
10. Light theme and dark theme variants
11. Core design system and reusable UI components

Do NOT fully design:

* Prediction workflow
* Prediction results detail
* Prediction history table
* Prediction detail page
* Reports analytics charts
* Admin management pages
* Monitoring dashboard

These destinations may appear in navigation but should not be built as full functional screens in this phase.

# PRODUCT DESIGN DIRECTION

The visual style should feel like a premium enterprise AI/ML platform.

Think:

* Modern
* Technical
* Trustworthy
* Precise
* Calm
* Professional
* High-end SaaS dashboard
* Suitable for an AI/ML Engineer portfolio

The product should feel closer to a modern research platform or developer-focused SaaS product than a traditional hospital website.

Avoid:

* Generic hospital website design
* Stock doctor imagery
* Stethoscopes
* Red crosses
* Decorative medical illustrations
* Excessive gradients
* Glossy 3D elements
* Overly colorful dashboards
* Fake analytics

Use:

* Clean grid system
* Generous whitespace
* Restrained color palette
* Strong typography hierarchy
* Technical details styled with optional monospace typography
* Minimal, meaningful iconography

# AUTHENTICATED APPLICATION STRUCTURE

Create a collapsible left sidebar.

Navigation structure:

Primary Navigation:

* Dashboard
* Predict
* History
* Reports

Secondary Navigation:

* Profile
* Settings

Admin-only section:

* Admin: Users
* Admin: History
* Admin: System
* Admin: Monitoring

Create two sidebar variants:

1. Standard User

   * Admin section hidden

2. Admin User

   * Admin section visible

The sidebar should support:

* Default state
* Hover state
* Active state
* Collapsed desktop state
* Mobile drawer state

# TOP BAR

Create a clean enterprise-style top bar.

Left side:

* Breadcrumb or page title

Right side:

* AI runtime/system status indicator
* Clearly presented as a placeholder backend-connected state, NOT a fake live claim
* User avatar
* User name
* Role badge
* User menu
* Logout action

Example placeholder wording:

"AI Runtime Status"
"Connect to backend"

Do NOT show fake uptime percentages or fabricated live system values.

# LOGIN SCREEN

Create a centered authentication card.

Fields:

* Email
* Password

Actions:

Primary:
"Sign In"

Secondary:
"Create an account"

Include UI variants:

* Default
* Focused field
* Validation error
* Invalid credentials error
* Loading/submitting state
* Disabled button state

The screen should feel secure, clean, and professional without looking like a banking application.

# REGISTER SCREEN

Use the same visual authentication system.

Fields:

* Full Name
* Email
* Password
* Confirm Password

Actions:

Primary:
"Create Account"

Secondary:
"Already have an account? Sign In"

Include:

* Validation error state
* Password mismatch state
* Loading/submitting state
* Disabled button state

# DASHBOARD — STRUCTURAL FOUNDATION ONLY

Create the dashboard as a visual foundation.

Include:

1. Welcome header
   Example:
   "Welcome back"
   Use a generic placeholder name if needed.

2. Summary card area

Create 3–4 cards, but DO NOT use fabricated numerical statistics.

Instead use clear placeholder or disconnected states such as:

* "Recent Predictions"
  "Connect to backend to load activity"

* "Model Availability"
  "System data unavailable"

* "Analysis Activity"
  Skeleton loading state

* "System Status"
  "Awaiting backend data"

Do NOT show:

* Fake prediction counts
* Fake accuracy percentages
* Fake patient numbers
* Fake performance metrics
* Fake uptime
* Fake charts

3. Quick Action

Create a prominent but restrained action card:

"Start New Prediction"

Description:
"Upload a supported histopathology image to begin AI-assisted analysis."

The action conceptually links to:

/predict

4. Recent Activity

Create an empty state:

"No predictions yet"

Supporting text:

"Analyze your first image to see activity here."

Include a CTA:

"Start Prediction"

# REUSABLE UI STATE SYSTEM

Design reusable state patterns that can be used across future pages.

## Loading

Create skeleton components for:

* Metric/status card
* List item
* Table row
* Content section
* Page loading

## Empty

Include:

* Simple icon
* Short title
* Supporting message
* Optional primary CTA

## Error

Include:

* Error icon
* Clear message
* Retry action

Keep validation errors visually distinct from system/API errors.

# DESIGN SYSTEM

Create a reusable component system.

## Typography

Use:

* Clean modern sans-serif for UI
* Optional monospace accents for:

  * IDs
  * timestamps
  * confidence values
  * technical/system information

Create clear hierarchy:

* Display/page title
* Section heading
* Card title
* Body text
* Small metadata
* Technical label

## Color System

Use:

* Restrained clinical blue or teal primary accent
* Neutral grays for surfaces and structure
* Semantic colors only for:

  * Success
  * Warning
  * Error
  * Information

Avoid excessive color usage.

Provide both:

* Light theme
* Dark theme

The dark theme should feel like a premium technical dashboard, not pure black.

## Spacing

Use an 8px spacing grid.

Prioritize:

* Generous whitespace
* Consistent card padding
* Clear separation between sections
* Dense but readable desktop layouts

## Core Components

Create reusable variants for:

* Button

  * Primary
  * Secondary
  * Ghost
  * Destructive
  * Disabled
  * Loading

* Input

  * Default
  * Focus
  * Error
  * Disabled

* Card

* Badge

  * User role
  * System status

* Sidebar navigation item

* Avatar

* Dropdown/user menu

* Skeleton loader

* Empty state

* Error state

* Toast notification

# RESPONSIVE DESIGN

Primary target:

* 1440px desktop
* 1280px desktop

Also define:

Tablet:

* Sidebar becomes compact icon rail

Mobile:

* Sidebar becomes slide-over drawer
* Top bar remains accessible
* Cards stack vertically
* Forms use full-width layout
* Maintain comfortable touch targets

# INTERACTION DIRECTION

Define subtle interaction behavior:

* Sidebar transitions
* Navigation hover/active states
* Button hover/disabled/loading states
* Form focus/error states
* Dropdown and modal transitions

Use subtle transitions around:

150–200ms ease-out

Avoid:

* Heavy animation
* Large animated charts
* Distracting motion
* Decorative motion on data-dense areas

# IMPORTANT CONTENT RULES

Do NOT include:

* Real patient data
* Fake patient profiles
* Fake diagnosis information
* Fake accuracy metrics
* Fake ROC/F1/precision/recall charts
* Fake live analytics
* Fake model performance leaderboards
* Unsupported functionality

Any data-dependent dashboard component must use:

* Skeleton state
* Empty state
* Error state
* "Connect to backend"
* "Awaiting system data"

rather than fabricated values.

# FINAL OUTPUT

Create a polished, consistent Phase 1 Figma design system and screen set containing:

* Login
* Register
* Standard user app shell
* Admin user sidebar variant
* Dashboard structural foundation
* Loading state components
* Empty state components
* Error state components
* Light theme
* Dark theme
* Responsive desktop/tablet/mobile behavior

The final design should look like a cohesive, enterprise-grade AI/ML SaaS product ready for incremental implementation in React, TypeScript, Tailwind CSS, and Shadcn UI.
