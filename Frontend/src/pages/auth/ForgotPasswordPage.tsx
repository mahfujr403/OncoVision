import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Mail, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { DemoDataBanner } from '@/components/ui/DemoDataBanner';
import { ROUTES } from '@/constants/routes';
import { forgotPasswordSchema, type ForgotPasswordFormData } from '@/utils/validation';
import { AuthErrorAlert } from '@/features/auth';

// There is no forgot-password / password-reset-email endpoint on the
// backend today — verified against app/api/v1/auth.py. This form is left
// in place (per project rule against removing unsupported features
// outright) but cannot actually send anything; it always surfaces the
// explanatory error below instead of faking a "sent" state.
export default function ForgotPasswordPage() {
  const [serverError, setServerError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (_data: ForgotPasswordFormData) => {
    setServerError('The backend has no password-reset endpoint yet, so a reset email cannot be sent.');
  };

  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold font-display">Reset password</h1>
        <p className="text-sm text-muted-foreground">
          Enter your email and we'll send a reset link.
        </p>
      </div>

      <DemoDataBanner feature="password reset" />

      {serverError && <AuthErrorAlert message={serverError} />}

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        noValidate
        aria-label="Password reset form"
      >
        <Input
          label="Email"
          type="email"
          placeholder="you@institution.org"
          startAdornment={<Mail className="h-3.5 w-3.5" />}
          error={errors.email?.message}
          autoComplete="email"
          autoFocus
          {...register('email')}
        />

        <Button type="submit" className="w-full" loading={isSubmitting} disabled={isSubmitting}>
          {isSubmitting ? 'Sending reset link...' : 'Send reset link'}
        </Button>
      </form>

      <Link
        to={ROUTES.LOGIN}
        className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to sign in
      </Link>
    </div>
  );
}
