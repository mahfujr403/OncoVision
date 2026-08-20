import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Lock, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { ROUTES } from '@/constants/routes';
import { resetPasswordSchema, type ResetPasswordFormData } from '@/utils/validation';
import { AuthErrorAlert, PasswordStrength, usePasswordToggle } from '@/features/auth';

// There is no reset-password (token-exchange) endpoint on the backend
// today — verified against app/api/v1/auth.py. Submitting always surfaces
// the explanatory error rather than faking success.
export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [serverError, setServerError] = useState('');
  const { visible: showPwd, toggle: togglePwd, inputType: pwdType } = usePasswordToggle();
  const { visible: showConfirm, toggle: toggleConfirm, inputType: confirmType } = usePasswordToggle();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  const password = watch('password') ?? '';

  const onSubmit = async (_data: ResetPasswordFormData) => {
    setServerError('The backend has no password-reset endpoint yet, so this cannot be completed.');
  };

  if (!token) {
    return (
      <div className="space-y-5 text-center">
        <div className="flex justify-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-7 w-7 text-destructive" />
          </div>
        </div>
        <div className="space-y-1">
          <h1 className="text-xl font-bold font-display">Invalid reset link</h1>
          <p className="text-sm text-muted-foreground">
            This reset link is missing or invalid. Please request a new one.
          </p>
        </div>
        <Button asChild className="w-full">
          <Link to={ROUTES.FORGOT_PASSWORD}>Request new link</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold font-display">New password</h1>
        <p className="text-sm text-muted-foreground">Choose a strong password for your account.</p>
      </div>

      <DemoDataBanner feature="password reset" />

      {serverError && <AuthErrorAlert message={serverError} />}

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        noValidate
        aria-label="Set new password form"
      >
        <div className="space-y-1.5">
          <Input
            label="New password"
            type={pwdType}
            placeholder="Min. 8 chars, uppercase, number"
            startAdornment={<Lock className="h-3.5 w-3.5" />}
            endAdornment={
              <button type="button" onClick={togglePwd} aria-label={showPwd ? 'Hide' : 'Show'}>
                {showPwd ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            }
            error={errors.password?.message}
            autoComplete="new-password"
            autoFocus
            {...register('password')}
          />
          <PasswordStrength password={password} />
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

        <Button type="submit" className="w-full" loading={isSubmitting} disabled={isSubmitting}>
          {isSubmitting ? 'Updating password...' : 'Update password'}
        </Button>
      </form>
    </div>
  );
}
