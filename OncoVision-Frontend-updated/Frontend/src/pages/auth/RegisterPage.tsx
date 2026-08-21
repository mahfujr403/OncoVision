import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Lock, Mail, User } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ROUTES } from '@/constants/routes';
import { registerSchema, type RegisterFormData } from '@/utils/validation';
import { authService, AuthErrorAlert, PasswordStrength, usePasswordToggle } from '@/features/auth';
import type { ApiError } from '@/types';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState('');
  const { visible: showPwd, toggle: togglePwd, inputType: pwdType } = usePasswordToggle();
  const { visible: showConfirm, toggle: toggleConfirm, inputType: confirmType } = usePasswordToggle();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const password = watch('password') ?? '';

  const onSubmit = async (data: RegisterFormData) => {
    setServerError('');
    try {
      // New accounts are always created with role="user" by the backend —
      // there is no role field to send here.
      await authService.register({
        full_name: data.name,
        email: data.email,
        password: data.password,
        confirm_password: data.confirmPassword,
      });
      toast.success('Account created! Please sign in.', { duration: 4000 });
      navigate(ROUTES.LOGIN);
    } catch (err) {
      const apiErr = err as ApiError;
      setServerError(apiErr.message ?? 'Registration failed. Please try again.');
    }
  };

  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold font-display">Create account</h1>
        <p className="text-sm text-muted-foreground">
          Join the OncoVision AI platform. New accounts are created with standard user access.
        </p>
      </div>

      {serverError && <AuthErrorAlert message={serverError} />}

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-3"
        noValidate
        aria-label="Registration form"
      >
        <Input
          label="Full name"
          placeholder="Dr. Jane Smith"
          startAdornment={<User className="h-3.5 w-3.5" />}
          error={errors.name?.message}
          autoComplete="name"
          autoFocus
          {...register('name')}
        />

        <Input
          label="Email"
          type="email"
          placeholder="you@institution.org"
          startAdornment={<Mail className="h-3.5 w-3.5" />}
          error={errors.email?.message}
          autoComplete="email"
          {...register('email')}
        />

        <div className="space-y-1.5">
          <Input
            label="Password"
            type={pwdType}
            placeholder="Min. 8 chars, uppercase, number"
            startAdornment={<Lock className="h-3.5 w-3.5" />}
            endAdornment={
              <button
                type="button"
                onClick={togglePwd}
                aria-label={showPwd ? 'Hide password' : 'Show password'}
              >
                {showPwd ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            }
            error={errors.password?.message}
            autoComplete="new-password"
            {...register('password')}
          />
          <PasswordStrength password={password} />
        </div>

        <Input
          label="Confirm password"
          type={confirmType}
          placeholder="Repeat your password"
          startAdornment={<Lock className="h-3.5 w-3.5" />}
          endAdornment={
            <button
              type="button"
              onClick={toggleConfirm}
              aria-label={showConfirm ? 'Hide password' : 'Show password'}
            >
              {showConfirm ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          }
          error={errors.confirmPassword?.message}
          autoComplete="new-password"
          {...register('confirmPassword')}
        />

        <Button
          type="submit"
          className="w-full mt-1"
          loading={isSubmitting}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Creating account...' : 'Create account'}
        </Button>
      </form>

      <p className="text-center text-xs text-muted-foreground">
        Already have an account?{' '}
        <Link to={ROUTES.LOGIN} className="text-primary hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}
