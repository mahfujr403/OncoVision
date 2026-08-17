import { useState } from 'react';
import * as Switch from '@radix-ui/react-switch';
import * as Tabs from '@radix-ui/react-tabs';
import { Monitor, Sun, Moon, Bell, Shield, UserCog, Clock, Globe } from 'lucide-react';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useTheme } from '@/hooks/useTheme';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';
import { Link } from 'react-router-dom';
import { ROUTES } from '@/constants/routes';
import { formatDateTime } from '@/utils/formatters';

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
  const { user, logout } = useAuth();

  // Notification states
  const [emailNotifs, setEmailNotifs] = useState(true);
  const [predictionAlerts, setPredictionAlerts] = useState(true);
  const [modelUpdates, setModelUpdates] = useState(false);
  const [weeklyDigest, setWeeklyDigest] = useState(true);
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false);

  const sessionData = [
    { label: 'Current device', value: 'Chrome on macOS' },
    { label: 'IP address', value: '10.0.0.12' },
    { label: 'Last active', value: formatDateTime(user?.last_login ?? new Date().toISOString()) },
    { label: 'Session expires', value: 'In 14 days (remember me)' },
  ];

  return (
    <div className="space-y-5 max-w-2xl">
      <SectionTitle title="Settings" description="Manage your platform preferences" />

      <Tabs.Root value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)}>
        {/* Tab list */}
        <Tabs.List
          aria-label="Settings categories"
          className="flex gap-0.5 rounded-lg bg-secondary p-1 mb-5 overflow-x-auto"
        >
          {TABS.map((tab) => (
            <Tabs.Trigger
              key={tab.id}
              value={tab.id}
              className={cn(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors',
                'focus:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                'data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm',
                'data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground',
              )}
            >
              {tab.icon}
              {tab.label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {/* General */}
        <Tabs.Content value="general" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Language & Region</CardTitle>
              <CardDescription>Display language and date format preferences</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <Globe className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Language</p>
                    <p className="text-xs text-muted-foreground">Interface language</p>
                  </div>
                </div>
                <select className="h-8 rounded-md border border-border bg-secondary px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring">
                  <option>English (US)</option>
                  <option>English (UK)</option>
                </select>
              </div>
              <div className="flex items-center justify-between gap-4 pt-1 border-t border-border">
                <div>
                  <p className="text-sm font-medium">Date format</p>
                  <p className="text-xs text-muted-foreground">How dates are displayed</p>
                </div>
                <select className="h-8 rounded-md border border-border bg-secondary px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring">
                  <option>MMM D, YYYY</option>
                  <option>DD/MM/YYYY</option>
                  <option>YYYY-MM-DD</option>
                </select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Data & Privacy</CardTitle>
              <CardDescription>Control how your data is used on the platform</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ToggleSetting
                label="Analytics usage"
                description="Help improve OncoVision AI with anonymised usage data"
                checked={true}
                onCheckedChange={() => {}}
              />
              <ToggleSetting
                label="Crash reports"
                description="Automatically send error reports to improve stability"
                checked={false}
                onCheckedChange={() => {}}
              />
            </CardContent>
          </Card>
        </Tabs.Content>

        {/* Appearance */}
        <Tabs.Content value="appearance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Theme</CardTitle>
              <CardDescription>Choose your preferred interface theme</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                {(['dark', 'light'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTheme(t)}
                    aria-pressed={theme === t}
                    className={cn(
                      'flex flex-col items-center gap-2 rounded-lg border px-3 py-4 text-sm font-medium transition-all',
                      'focus:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                      theme === t
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border hover:bg-muted/30 text-muted-foreground',
                    )}
                  >
                    {t === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
                    {t === 'dark' ? 'Dark' : 'Light'}
                    {theme === t && <Badge variant="default" className="text-[10px]">Active</Badge>}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Density</CardTitle>
              <CardDescription>Adjust the information density of the interface</CardDescription>
            </CardHeader>
            <CardContent className="flex gap-2">
              {['Compact', 'Default', 'Comfortable'].map((d, i) => (
                <button
                  key={d}
                  className={cn(
                    'flex-1 rounded-md border px-3 py-2 text-xs font-medium transition-colors',
                    i === 1
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border text-muted-foreground hover:bg-muted/30',
                  )}
                >
                  {d}
                </button>
              ))}
            </CardContent>
          </Card>
        </Tabs.Content>

        {/* Notifications */}
        <Tabs.Content value="notifications" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Email Notifications</CardTitle>
              <CardDescription>Control which emails you receive</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ToggleSetting
                label="Prediction results"
                description="Email when a prediction completes"
                checked={emailNotifs}
                onCheckedChange={setEmailNotifs}
              />
              <ToggleSetting
                label="High-confidence only"
                description="Only notify for predictions with confidence &gt; 90%"
                checked={highConfidenceOnly}
                onCheckedChange={setHighConfidenceOnly}
              />
              <ToggleSetting
                label="Model updates"
                description="Email when ensemble models are updated"
                checked={modelUpdates}
                onCheckedChange={setModelUpdates}
              />
              <ToggleSetting
                label="Weekly digest"
                description="Summary of your activity every Monday"
                checked={weeklyDigest}
                onCheckedChange={setWeeklyDigest}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>In-App Notifications</CardTitle>
              <CardDescription>Notifications shown inside the platform</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ToggleSetting
                label="Prediction alerts"
                description="Banner when a prediction completes"
                checked={predictionAlerts}
                onCheckedChange={setPredictionAlerts}
              />
              <ToggleSetting
                label="System announcements"
                description="Maintenance windows and platform updates"
                checked={true}
                onCheckedChange={() => {}}
              />
            </CardContent>
          </Card>
        </Tabs.Content>

        {/* Security */}
        <Tabs.Content value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Password</CardTitle>
              <CardDescription>Manage your account password</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground mb-3">
                Use a strong password with at least 8 characters, one uppercase letter, and one number.
              </p>
              <Button size="sm" asChild>
                <Link to={ROUTES.CHANGE_PASSWORD}>Change password</Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Two-Factor Authentication</CardTitle>
              <CardDescription>Add an extra layer of security to your account</CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Badge variant="warning" dot>Not enabled</Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  2FA setup will be available in a future release.
                </p>
              </div>
              <Button size="sm" variant="outline" disabled>Enable 2FA</Button>
            </CardContent>
          </Card>

          <Card className="border-destructive/30">
            <CardHeader>
              <CardTitle className="text-destructive">Danger Zone</CardTitle>
              <CardDescription>Irreversible actions — proceed with caution</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium">Delete account</p>
                  <p className="text-xs text-muted-foreground">Permanently remove your account and all data</p>
                </div>
                <Button variant="destructive" size="sm" disabled>Delete</Button>
              </div>
            </CardContent>
          </Card>
        </Tabs.Content>

        {/* Session */}
        <Tabs.Content value="session" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Current Session</CardTitle>
              <CardDescription>Details about your active login session</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {sessionData.map((s) => (
                <div key={s.label} className="flex items-center justify-between gap-4 py-1">
                  <span className="text-xs text-muted-foreground">{s.label}</span>
                  <span className="text-xs font-medium font-mono">{s.value}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Session Management</CardTitle>
              <CardDescription>Control your active sessions across devices</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ToggleSetting
                label="Remember this device"
                description="Stay signed in for 30 days on this browser"
                checked={true}
                onCheckedChange={() => {}}
              />
              <div className="pt-2 border-t border-border space-y-2">
                <Button variant="outline" size="sm" onClick={() => { logout(); }}>
                  Sign out this session
                </Button>
                <p className="text-xs text-muted-foreground">
                  Active sessions on other devices can't be revoked yet (coming soon).
                </p>
              </div>
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
    <div className="flex items-center justify-between gap-4 py-0.5">
      <div className="flex-1">
        <label htmlFor={id} className="text-sm font-medium cursor-pointer">{label}</label>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <Switch.Root
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        aria-label={label}
        className={cn(
          'relative h-5 w-9 rounded-full transition-colors outline-none',
          'focus-visible:ring-1 focus-visible:ring-ring',
          checked ? 'bg-primary' : 'bg-secondary border border-border',
        )}
      >
        <Switch.Thumb
          className={cn(
            'block h-4 w-4 rounded-full bg-white shadow-sm transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0.5',
          )}
        />
      </Switch.Root>
    </div>
  );
}
