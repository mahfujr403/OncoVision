import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Lock, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { changePasswordSchema, type ChangePasswordFormData } from '@/utils/validation';
import { AuthErrorAlert, PasswordStrength, usePasswordToggle } from '@/features/auth';
import { useAuth } from '@/hooks/useAuth';

export default function ChangePasswordPage() {
  const { user } = useAuth();
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
  // backend today — verified against app/api/v1/auth.py. Submitting can't
  // actually update anything, so this is left disabled with a demo banner
  // rather than faking a success toast.
  const onSubmit = async (_data: ChangePasswordFormData) => {
    if (!user) return;
    setServerError('The backend has no change-password endpoint yet, so this form cannot submit.');
  };

  return (
    <div className="space-y-5 max-w-md">
      <SectionTitle
        title="Change Password"
        description="Update your account password"
      />

      <DemoDataBanner feature="change-password" />

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <ShieldCheck className="h-4 w-4 text-primary" />
            </div>
            <div>
              <CardTitle>Password Security</CardTitle>
              <CardDescription>Use a strong, unique password</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {serverError && <AuthErrorAlert message={serverError} className="mb-4" />}

          <form
            onSubmit={handleSubmit(onSubmit)}
            className="space-y-4"
            noValidate
            aria-label="Change password form"
          >
            <Input
              label="Current password"
              type={currentType}
              placeholder="Your current password"
              startAdornment={<Lock className="h-3.5 w-3.5" />}
              endAdornment={
                <button type="button" onClick={toggleCurrent} aria-label={showCurrent ? 'Hide' : 'Show'}>
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
                label="New password"
                type={newType}
                placeholder="Min. 8 chars, uppercase, number"
                startAdornment={<Lock className="h-3.5 w-3.5" />}
                endAdornment={
                  <button type="button" onClick={toggleNew} aria-label={showNew ? 'Hide' : 'Show'}>
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
              label="Confirm new password"
              type={confirmType}
              placeholder="Repeat your new password"
              startAdornment={<Lock className="h-3.5 w-3.5" />}
              endAdornment={
                <button type="button" onClick={toggleConfirm} aria-label={showConfirm ? 'Hide' : 'Show'}>
                  {showConfirm ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              }
              error={errors.confirmPassword?.message}
              autoComplete="new-password"
              {...register('confirmPassword')}
            />

            <div className="flex gap-2 pt-1">
              <Button type="submit" loading={isSubmitting} disabled title="No backend endpoint yet">
                Update password
              </Button>
              <Button type="button" variant="ghost" onClick={() => reset()}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
