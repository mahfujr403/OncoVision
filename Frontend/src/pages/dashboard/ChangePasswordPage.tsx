import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Lock, ShieldCheck, KeyRound, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { changePasswordSchema, type ChangePasswordFormData } from '@/utils/validation';
import { AuthErrorAlert, PasswordStrength, usePasswordToggle } from '@/features/auth';
import { useAuth } from '@/hooks/useAuth';
import { ROUTES } from '@/constants/routes';

export default function ChangePasswordPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState('');
  const { visible: showCurrent, toggle: toggleCurrent, inputType: currentType } = usePasswordToggle();
  const { visible: showNew, toggle: toggleNew, inputType: newType } = usePasswordToggle();
  const { visible: showConfirm, toggle: toggleConfirm, inputType: confirmType } = usePasswordToggle();

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
  });

  const newPassword = watch('newPassword') ?? '';

  // There is no change-password (or any account-mutation) endpoint on the
  // backend today — verified against app/api/v1/auth.py. Submitting cannot
  // update credentials remotely, so submission is disabled with a demo banner
  // rather than generating misleading success states.
  const onSubmit = async (_data: ChangePasswordFormData) => {
    if (!user) return;
    setServerError('The backend authentication service has not enabled self-service password modifications.');
  };

  return (
    <div className="space-y-6 max-w-lg">
      {/* Calm Scientific Header with Back Link */}
      <div>
        <div className="mb-2">
          <Button variant="ghost" size="sm" asChild className="gap-1.5 text-xs text-text-muted hover:text-text-primary -ml-2">
            <Link to={ROUTES.SETTINGS}>
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Settings</span>
            </Link>
          </Button>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-text-primary sm:text-2xl">
          Change Account Password
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          Update authorization credentials for your OncoVision AI workspace account.
        </p>
      </div>

      <DemoDataBanner feature="change-password" />

      <Card className="p-5 sm:p-6 space-y-5">
        <CardHeader className="p-0">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-surface text-primary border border-primary/20">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-base">Credential Security</CardTitle>
              <CardDescription>
                Passwords must be at least 8 characters and include at least one uppercase letter and one number.
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 pt-2">
          {serverError && <AuthErrorAlert message={serverError} className="mb-4" />}

          <form
            onSubmit={handleSubmit(onSubmit)}
            className="space-y-4"
            noValidate
            aria-label="Change password form"
          >
            <Input
              label="Current Password"
              type={currentType}
              placeholder="Enter current password"
              startAdornment={<Lock className="h-3.5 w-3.5" />}
              endAdornment={
                <button
                  type="button"
                  onClick={toggleCurrent}
                  aria-label={showCurrent ? 'Hide current password' : 'Show current password'}
                  className="p-1 rounded text-text-muted hover:text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
                >
                  {showCurrent ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              }
              error={errors.currentPassword?.message}
              autoComplete="current-password"
              autoFocus
              {...register('currentPassword')}
            />

            <div className="space-y-1.5">
              <Input
                label="New Password"
                type={newType}
                placeholder="Min. 8 characters with uppercase and digit"
                startAdornment={<KeyRound className="h-3.5 w-3.5" />}
                endAdornment={
                  <button
                    type="button"
                    onClick={toggleNew}
                    aria-label={showNew ? 'Hide new password' : 'Show new password'}
                    className="p-1 rounded text-text-muted hover:text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
                  >
                    {showNew ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                }
                error={errors.newPassword?.message}
                autoComplete="new-password"
                {...register('newPassword')}
              />
              <PasswordStrength password={newPassword} />
            </div>

            <Input
              label="Confirm New Password"
              type={confirmType}
              placeholder="Repeat your new password"
              startAdornment={<Lock className="h-3.5 w-3.5" />}
              endAdornment={
                <button
                  type="button"
                  onClick={toggleConfirm}
                  aria-label={showConfirm ? 'Hide confirmed password' : 'Show confirmed password'}
                  className="p-1 rounded text-text-muted hover:text-text-primary focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-primary"
                >
                  {showConfirm ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              }
              error={errors.confirmPassword?.message}
              autoComplete="new-password"
              {...register('confirmPassword')}
            />

            <div className="flex items-center gap-2.5 pt-3 border-t border-border-subtle">
              <Button
                type="submit"
                loading={isSubmitting}
                disabled
                title="Self-service password update is a planned feature"
              >
                Update Password
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  reset();
                  navigate(ROUTES.SETTINGS);
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
