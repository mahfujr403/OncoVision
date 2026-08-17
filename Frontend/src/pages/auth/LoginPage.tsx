import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ROUTES } from '@/constants/routes';
import { loginSchema, type LoginFormData } from '@/utils/validation';
import { AuthErrorAlert, usePasswordToggle, useLogin } from '@/features/auth';
import { useAuth } from '@/hooks/useAuth';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const loginMutation = useLogin();
  const { visible, toggle, inputType } = usePasswordToggle();

  const from =
    (location.state as { from?: Location })?.from?.pathname ?? ROUTES.DASHBOARD;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      const result = await loginMutation.mutateAsync({
        email: data.email,
        password: data.password,
      });
      login(result.user, result.access_token, result.refresh_token);
      toast.success(`Welcome back, ${result.user.full_name.split(' ')[0]}!`);
      navigate(from, { replace: true });
    } catch {
      // error surfaced via loginMutation.error below
    }
  };

  const isPending = isSubmitting || loginMutation.isPending;
  const serverError =
    loginMutation.error?.message ?? null;

  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold font-display">Sign in</h1>
        <p className="text-sm text-muted-foreground">
          Access your OncoVision AI workspace
        </p>
      </div>

      {serverError && <AuthErrorAlert message={serverError} />}

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        noValidate
        aria-label="Sign in form"
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

        <Input
          label="Password"
          type={inputType}
          placeholder="Enter your password"
          startAdornment={<Lock className="h-3.5 w-3.5" />}
          endAdornment={
            <button
              type="button"
              onClick={toggle}
              aria-label={visible ? 'Hide password' : 'Show password'}
              className="focus:outline-none focus:ring-1 focus:ring-ring rounded"
            >
              {visible ? (
                <EyeOff className="h-3.5 w-3.5" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
            </button>
          }
          error={errors.password?.message}
          autoComplete="current-password"
          {...register('password')}
        />

        <div className="flex items-center justify-between">
          <Link
            to={ROUTES.FORGOT_PASSWORD}
            className="text-xs text-primary hover:underline focus:outline-none focus:ring-1 focus:ring-ring rounded"
          >
            Forgot password?
          </Link>
        </div>

        <Button
          type="submit"
          className="w-full"
          loading={isPending}
          disabled={isPending}
        >
          {isPending ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

      <p className="text-center text-xs text-muted-foreground">
        {"Don't have an account? "}
        <Link to={ROUTES.REGISTER} className="text-primary hover:underline font-medium">
          Create account
        </Link>
      </p>
    </div>
  );
}
