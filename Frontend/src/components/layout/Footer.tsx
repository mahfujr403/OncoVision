import type { SVGProps } from 'react';
import { Mail, Globe, ArrowUpRight, Stethoscope } from 'lucide-react';
import { APP_NAME, APP_TAGLINE } from '@/constants/app';
import { DEVELOPER, PROJECT_REPO_URL } from '@/constants/site';
import { Button } from '@/components/ui/Button';

// `lucide-react` (this project's version) ships no brand glyphs, so GitHub
// and LinkedIn are small inline SVGs sized to match the lucide icon set.
function GithubIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M12 .5C5.65.5.5 5.66.5 12.03c0 5.1 3.29 9.42 7.86 10.95.58.1.79-.25.79-.56 0-.28-.01-1.02-.02-2-3.2.7-3.88-1.54-3.88-1.54-.52-1.33-1.28-1.69-1.28-1.69-1.04-.72.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.56-.29-5.25-1.28-5.25-5.71 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.47.11-3.06 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.77.11 3.06.74.81 1.19 1.84 1.19 3.1 0 4.44-2.7 5.42-5.27 5.7.41.36.78 1.08.78 2.17 0 1.57-.01 2.83-.01 3.22 0 .31.21.67.8.56A10.53 10.53 0 0 0 23.5 12.03C23.5 5.66 18.35.5 12 .5Z" />
    </svg>
  );
}

function LinkedinIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.15 1.45-2.15 2.94v5.67H9.34V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29ZM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13ZM7.12 20.45H3.56V9h3.56v11.45Z" />
    </svg>
  );
}

const SOCIAL_LINKS = [
  { label: 'LinkedIn', href: DEVELOPER.linkedin, icon: LinkedinIcon },
  { label: 'GitHub', href: DEVELOPER.github, icon: GithubIcon },
  { label: 'Email', href: `mailto:${DEVELOPER.email}`, icon: Mail },
  { label: 'Portfolio', href: DEVELOPER.portfolio, icon: Globe },
] as const;

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-card/30">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="grid gap-8 md:grid-cols-2 md:gap-6">
          {/* Brand — app name links to the project repo */}
          <div>
            <a
              href={PROJECT_REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="group inline-flex items-center gap-2.5"
              aria-label={`${APP_NAME} — view source on GitHub`}
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                <Stethoscope className="h-4 w-4 text-primary-foreground" />
              </div>
              <span className="font-semibold font-display text-sm transition-colors group-hover:text-primary">
                {APP_NAME}
              </span>
              <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
            </a>
            <p className="mt-3 max-w-xs text-xs leading-relaxed text-muted-foreground">
              {APP_TAGLINE}. Open-source — click the logo above to view the repository on GitHub.
            </p>
          </div>

          {/* Developer contact */}
          <div className="md:text-right">
            <p className="mb-2 text-xs text-muted-foreground">Developed by</p>
            <a
              href={DEVELOPER.portfolio}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-semibold font-display text-sm transition-colors hover:text-primary"
              aria-label={`${DEVELOPER.name} — visit portfolio`}
            >
              {DEVELOPER.name}
              <ArrowUpRight className="h-3.5 w-3.5" />
            </a>

            <div className="mt-3 flex items-center gap-2 md:justify-end">
              {SOCIAL_LINKS.map(({ label, href, icon: Icon }) => (
                <Button
                  key={label}
                  variant="outline"
                  size="icon-sm"
                  asChild
                  className="rounded-full"
                >
                  <a
                    href={href}
                    target={href.startsWith('mailto:') ? undefined : '_blank'}
                    rel={href.startsWith('mailto:') ? undefined : 'noopener noreferrer'}
                    aria-label={label}
                    title={label}
                  >
                    <Icon className="h-3.5 w-3.5" />
                  </a>
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-8 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 sm:flex-row">
          <p className="text-center text-[11px] text-muted-foreground sm:text-left">
            © {year}{' '}
            <a
              href={PROJECT_REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium hover:text-primary transition-colors"
            >
              {APP_NAME}
            </a>
            . Built for clinical research and oncological practice — not clinically approved.
          </p>

          <a
            href={PROJECT_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground transition-colors hover:text-primary"
          >
            <GithubIcon className="h-3 w-3" />
            {PROJECT_REPO_URL.replace('https://', '')}
          </a>
        </div>
      </div>
    </footer>
  );
}
