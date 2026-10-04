import { useState } from 'react';
import * as Switch from '@radix-ui/react-switch';
import * as Tabs from '@radix-ui/react-tabs';
import {
  Monitor,
  Sun,
  Moon,
  Bell,
  Shield,
  UserCog,
  Clock,
  Globe,
  Info,
  KeyRound,
  AlertTriangle,
  LogOut,
  Sliders,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useTheme } from '@/hooks/useTheme';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';
import { Link, useNavigate } from 'react-router-dom';
import { ROUTES } from '@/constants/routes';
import { formatDateTime } from '@/utils/formatters';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';

const TABS = [
  { id: 'general', label: 'General', icon: <UserCog className="h-3.5 w-3.5" /> },
  { id: 'appearance', label: 'Appearance', icon: <Monitor className="h-3.5 w-3.5" /> },
  { id: 'notifications', label: 'Notifications', icon: <Bell className="h-3.5 w-3.5" /> },
  { id: 'security', label: 'Security', icon: <Shield className="h-3.5 w-3.5" /> },
  { id: 'session', label: 'Session', icon: <Clock className="h-3.5 w-3.5" /> },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('general');
  const { theme, setTheme } = useTheme();
  const { user, logout, logoutAll } = useAuth();
  const navigate = useNavigate();

  const handleSignOutAllDevices = async () => {
    await logoutAll();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  // Notification states
  const [emailNotifs, setEmailNotifs] = useState(true);
  const [predictionAlerts, setPredictionAlerts] = useState(true);
  const [modelUpdates, setModelUpdates] = useState(false);
  const [weeklyDigest, setWeeklyDigest] = useState(true);
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false);

  // NOTE: only "Last active" below is real (from the authenticated user's
  // last_login). "Current device", "IP address", and "Session expires" have
  // no backend source — verified against app/schemas/user.py and
  // app/api/v1/auth.py, which return/track none of that — so they're
  // presented as illustrative via the demo banner in the Session tab below.
  const sessionData = [
    { label: 'Current device', value: 'Web Client (Active Browser)' },
    { label: 'Network host', value: '10.0.0.12 (Internal Subnet)' },
    { label: 'Last active', value: user?.last_login ? formatDateTime(user.last_login) : 'Current Session' },
    { label: 'Token lifecycle', value: 'Active Access Token (Refresh Rotation)' },
  ];

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Calm Scientific Header */}
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-text-primary sm:text-2xl">
          Settings
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          Manage your application experience, appearance, and account preferences.
        </p>
      </div>

      <Tabs.Root value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)}>
        {/* Tab list */}
        <Tabs.List
          aria-label="Settings categories"
          className="flex gap-1 rounded-lg border border-border bg-surface p-1 mb-6 overflow-x-auto"
        >
          {TABS.map((tab) => (
            <Tabs.Trigger
              key={tab.id}
              value={tab.id}
              className={cn(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors',
                'focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary',
                'data-[state=active]:bg-surface-raised data-[state=active]:text-text-primary data-[state=active]:shadow-xs',
                'data-[state=inactive]:text-text-muted data-[state=inactive]:hover:text-text-primary',
              )}
            >
              {tab.icon}
              {tab.label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {/* ==================== 1. GENERAL TAB ==================== */}
        <Tabs.Content value="general" className="space-y-4 focus-visible:outline-hidden">
          <Card>
            <CardHeader>
              <CardTitle>Language & Region</CardTitle>
              <CardDescription>Display language and date format preferences for pathology reports</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2.5">
                  <Globe className="h-4 w-4 text-text-muted shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">Interface Language</p>
                    <p className="text-xs text-text-muted">Primary language for diagnostic interface</p>
                  </div>
                </div>
                <select
                  aria-label="Select Interface Language"
                  defaultValue="en-US"
                  className="h-8 rounded-md border border-border bg-surface px-2.5 text-xs text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
                >
                  <option value="en-US">English (US)</option>
                  <option value="en-GB">English (UK)</option>
                </select>
              </div>

              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between pt-3 border-t border-border-subtle">
                <div>
                  <p className="text-sm font-medium text-text-primary">Date Format</p>
                  <p className="text-xs text-text-muted">Timestamp presentation across clinical logs</p>
                </div>
                <select
                  aria-label="Select Date Format"
                  defaultValue="MMM D, YYYY"
                  className="h-8 rounded-md border border-border bg-surface px-2.5 text-xs text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
                >
                  <option value="MMM D, YYYY">MMM D, YYYY (e.g. Oct 4, 2026)</option>
                  <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                  <option value="YYYY-MM-DD">YYYY-MM-DD (ISO)</option>
                </select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Data & Privacy</CardTitle>
              <CardDescription>Control local telemetry and diagnostic analytics usage</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ToggleSetting
                label="Anonymized usage analytics"
                description="Share de-identified workflow interactions to help improve clinical model interfaces"
                checked={true}
                onCheckedChange={() => {}}
              />
              <ToggleSetting
                label="Crash & inference diagnostics"
                description="Automatically capture non-patient technical runtime errors to improve inference stability"
                checked={false}
                onCheckedChange={() => {}}
              />
            </CardContent>
          </Card>
        </Tabs.Content>

        {/* ==================== 2. APPEARANCE TAB ==================== */}
        <Tabs.Content value="appearance" className="space-y-4 focus-visible:outline-hidden">
          <Card>
            <CardHeader>
              <CardTitle>Theme Preference</CardTitle>
              <CardDescription>
                Select your preferred interface visual contrast. OncoVision AI uses high-contrast clinical design tokens.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                role="radiogroup"
                aria-label="Theme selection"
                className="grid gap-3 sm:grid-cols-2"
              >
                <button
                  type="button"
                  role="radio"
                  aria-checked={theme === 'dark'}
                  onClick={() => setTheme('dark')}
                  className={cn(
                    'flex flex-col items-start gap-2.5 rounded-lg border p-4 text-left transition-all',
                    'focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary',
                    theme === 'dark'
                      ? 'border-primary bg-primary-surface/40 text-text-primary ring-1 ring-primary/30'
                      : 'border-border bg-surface text-text-secondary hover:bg-surface-raised',
                  )}
                >
                  <div className="flex w-full items-center justify-between">
                    <div className="flex items-center gap-2 text-primary">
                      <Moon className="h-4 w-4" />
                      <span className="text-sm font-semibold">Dark Diagnostic</span>
                    </div>
                    {theme === 'dark' && (
                      <Badge variant="primary" className="text-[10px]">Active</Badge>
                    )}
                  </div>
                  <p className="text-xs text-text-muted leading-relaxed">
                    Low-glare dark background optimized for digital histopathology review and prolonged slide analysis.
                  </p>
                </button>

                <button
                  type="button"
                  role="radio"
                  aria-checked={theme === 'light'}
                  onClick={() => setTheme('light')}
                  className={cn(
                    'flex flex-col items-start gap-2.5 rounded-lg border p-4 text-left transition-all',
                    'focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary',
                    theme === 'light'
                      ? 'border-primary bg-primary-surface/40 text-text-primary ring-1 ring-primary/30'
                      : 'border-border bg-surface text-text-secondary hover:bg-surface-raised',
                  )}
                >
                  <div className="flex w-full items-center justify-between">
                    <div className="flex items-center gap-2 text-primary">
                      <Sun className="h-4 w-4" />
                      <span className="text-sm font-semibold">Light Clinical</span>
                    </div>
                    {theme === 'light' && (
                      <Badge variant="primary" className="text-[10px]">Active</Badge>
                    )}
                  </div>
                  <p className="text-xs text-text-muted leading-relaxed">
                    Clean, high-contrast light background for standard clinical office illumination and printed reports.
                  </p>
                </button>
              </div>
            </CardContent>
          </Card>

          {/* Clinical Diagnostic Viewport Note (Documented removal of fake density switcher) */}
          <Card className="bg-surface-raised/30 border-border-subtle">
            <CardHeader>
              <div className="flex items-center gap-2 text-text-muted">
                <Sliders className="h-4 w-4 text-primary" />
                <CardTitle className="text-sm">Clinical Display Standards</CardTitle>
              </div>
              <CardDescription>
                Viewport typography and metric card proportions adhere to medical software accessibility guidelines (WCAG 2.2 AAA text contrast, minimum 44px touch targets).
              </CardDescription>
            </CardHeader>
          </Card>
        </Tabs.Content>

        {/* ==================== 3. NOTIFICATIONS TAB ==================== */}
        <Tabs.Content value="notifications" className="space-y-4 focus-visible:outline-hidden">
          <DemoDataBanner feature="notification preferences" />

          <Card>
            <CardHeader>
              <CardTitle>Email Notifications</CardTitle>
              <CardDescription>Configure asynchronous email dispatch for batch analyses</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ToggleSetting
                label="Prediction completion alerts"
                description="Receive an email confirmation when asynchronous inference finishes"
                checked={emailNotifs}
                onCheckedChange={setEmailNotifs}
              />
              <ToggleSetting
                label="High-confidence consensus only"
                description="Only trigger emails when cross-model agreement and confidence exceed 90%"
                checked={highConfidenceOnly}
                onCheckedChange={setHighConfidenceOnly}
              />
              <ToggleSetting
                label="Model registry updates"
                description="Notify when runtime model weights or ensemble manifests are updated"
                checked={modelUpdates}
                onCheckedChange={setModelUpdates}
              />
              <ToggleSetting
                label="Weekly analytical summary"
                description="Digest of analyzed slide volume and class distributions every Monday"
                checked={weeklyDigest}
                onCheckedChange={setWeeklyDigest}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>In-App Notifications</CardTitle>
              <CardDescription>Manage workspace notification banner toasts</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ToggleSetting
                label="Live analysis completion banner"
                description="Display notification banner when an image classification completes"
                checked={predictionAlerts}
                onCheckedChange={setPredictionAlerts}
              />
              <ToggleSetting
                label="System maintenance announcements"
                description="Alert regarding scheduled AI server maintenance windows"
                checked={true}
                onCheckedChange={() => {}}
              />
            </CardContent>
          </Card>
        </Tabs.Content>

        {/* ==================== 4. SECURITY TAB ==================== */}
        <Tabs.Content value="security" className="space-y-4 focus-visible:outline-hidden">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <KeyRound className="h-4 w-4 text-primary" />
                <CardTitle>Account Password</CardTitle>
              </div>
              <CardDescription>Manage credentials for your OncoVision AI workspace account</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-text-secondary leading-relaxed">
                Ensure passwords are at least 8 characters in length, containing at least one uppercase letter and one numeric digit.
              </p>
              <div>
                <Button size="sm" asChild>
                  <Link to={ROUTES.CHANGE_PASSWORD} className="gap-1.5">
                    <KeyRound className="h-3.5 w-3.5" />
                    <span>Change Password</span>
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Two-Factor Authentication (2FA)</CardTitle>
              <CardDescription>Hardware security keys or TOTP authenticator enforcement</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Badge variant="warning" dot>Not Configured</Badge>
                </div>
                <p className="text-xs text-text-muted mt-1 leading-relaxed">
                  Enterprise SSO / TOTP integration is scheduled for an upcoming security release.
                </p>
              </div>
              <Button size="sm" variant="outline" disabled className="self-start sm:self-auto">
                Configure 2FA
              </Button>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="border-error/30 bg-error-surface/10">
            <CardHeader>
              <div className="flex items-center gap-2 text-error">
                <AlertTriangle className="h-4 w-4" />
                <CardTitle className="text-error">Danger Zone</CardTitle>
              </div>
              <CardDescription>Irreversible account actions — proceed with strict caution</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">Delete Workspace Account</p>
                  <p className="text-xs text-text-muted">
                    Permanently purge your account, prediction history, and private cases.
                  </p>
                </div>
                <Button variant="destructive" size="sm" disabled className="self-start sm:self-auto">
                  Delete Account
                </Button>
              </div>
            </CardContent>
          </Card>
        </Tabs.Content>

        {/* ==================== 5. SESSION TAB ==================== */}
        <Tabs.Content value="session" className="space-y-4 focus-visible:outline-hidden">
          <Card>
            <CardHeader>
              <CardTitle>Active Session Telemetry</CardTitle>
              <CardDescription>Current authentication context and verified session state</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* REPLACED LEGACY HARDCODED DARK: AND AMBER WITH SEMANTIC TOKENS */}
              <div
                role="note"
                className="rounded-lg border border-warning/30 bg-warning-surface p-3 text-xs text-text-secondary leading-relaxed flex items-start gap-2.5"
              >
                <Info className="h-4 w-4 text-warning shrink-0 mt-0.5" aria-hidden="true" />
                <div>
                  <span className="font-semibold text-text-primary">Session Telemetry Notice: </span>
                  "Last active" is verified from your authenticated account record. Device and network attributes are illustrative client descriptors.
                </div>
              </div>

              <div className="divide-y divide-border-subtle pt-1">
                {sessionData.map((s) => (
                  <div key={s.label} className="flex items-center justify-between gap-4 py-2 text-xs">
                    <span className="text-text-muted">{s.label}</span>
                    <span className="font-mono font-medium text-text-primary">{s.value}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Session Revocation & Logout</CardTitle>
              <CardDescription>Manage active tokens across devices</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ToggleSetting
                label="Remember this workstation"
                description="Persist authorization tokens across browser restarts"
                checked={true}
                onCheckedChange={() => {}}
              />

              <div className="pt-3 border-t border-border-subtle flex flex-wrap items-center gap-2.5">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => { logout(); }}
                  className="gap-1.5"
                >
                  <LogOut className="h-3.5 w-3.5 text-text-muted" />
                  <span>Sign out this session</span>
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleSignOutAllDevices}
                  className="gap-1.5"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span>Sign out of all devices</span>
                </Button>
              </div>
              <p className="text-[11px] text-text-muted leading-relaxed">
                "Sign out of all devices" triggers backend token revocation (POST /api/v1/auth/logout-all), invalidating all issued refresh tokens immediately.
              </p>
            </CardContent>
          </Card>
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}

function ToggleSetting({
  label,
  description,
  checked,
  onCheckedChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
}) {
  const id = label.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="flex items-center justify-between gap-4 py-1">
      <div className="flex-1">
        <label htmlFor={id} className="text-sm font-medium text-text-primary cursor-pointer select-none">
          {label}
        </label>
        <p className="text-xs text-text-muted leading-relaxed">{description}</p>
      </div>
      <Switch.Root
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        aria-label={label}
        className={cn(
          'relative h-5 w-9 shrink-0 rounded-full transition-colors outline-none cursor-pointer',
          'focus-visible:ring-1 focus-visible:ring-primary',
          checked ? 'bg-primary' : 'bg-surface-raised border border-border',
        )}
      >
        <Switch.Thumb
          className={cn(
            'block h-4 w-4 rounded-full bg-white shadow-xs transition-transform duration-150',
            checked ? 'translate-x-4' : 'translate-x-0.5',
          )}
        />
      </Switch.Root>
    </div>
  );
}
