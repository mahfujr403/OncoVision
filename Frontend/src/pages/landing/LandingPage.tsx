import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Microscope, Brain, BarChart3, Shield, Zap, GitCompare,
  ArrowRight, Layers, CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { ROUTES } from '@/constants/routes';

const FEATURES = [
  {
    icon: <Brain className="h-5 w-5" />,
    title: 'Ensemble AI Consensus',
    description: 'Three distinct deep learning architectures combined via weighted probability voting for robust classification.',
  },
  {
    icon: <Microscope className="h-5 w-5" />,
    title: 'Histopathology Specialization',
    description: 'Trained specifically on lung and colon tissue histology for accurate morphological pattern recognition.',
  },
  {
    icon: <BarChart3 className="h-5 w-5" />,
    title: 'Verifiable Telemetry',
    description: 'Every inference outputs model-level confidence distributions, consensus ratios, and latency metrics.',
  },
  {
    icon: <Shield className="h-5 w-5" />,
    title: 'Research & Decision Support',
    description: 'Investigational platform designed for academic and laboratory research with transparent evidence reporting.',
  },
  {
    icon: <Zap className="h-5 w-5" />,
    title: 'Sub-Second Execution',
    description: 'High-throughput inference pipeline producing multi-model evaluation results in milliseconds.',
  },
  {
    icon: <GitCompare className="h-5 w-5" />,
    title: 'Evaluation Archive',
    description: 'Comprehensive case history tracking with individual estimator breakdowns and exportable reports.',
  },
];

const MODELS = [
  { name: 'MobileNetV2', type: 'Lightweight Inverted Residuals', weight: '0.30' },
  { name: 'DenseNet121', type: 'Densely Connected Convolutional', weight: '0.33' },
  { name: 'EfficientNetV2B0 + ResNet50 Fusion', type: 'Hybrid Feature Concatenation', weight: '0.37' },
];

const WORKFLOW_STEPS = [
  {
    step: '01',
    title: 'Slide Ingestion',
    description: 'Drag and drop standard H&E stained histopathology slide tiles in JPEG, PNG, or TIFF formats.',
  },
  {
    step: '02',
    title: 'Ensemble Inference',
    description: 'Constituent neural networks analyze cellular morphology independently in parallel runtime workers.',
  },
  {
    step: '03',
    title: 'Consensus & Evidence',
    description: 'Inspect weighted ensemble predictions, concordance ratios, and generated clinical decision-support summaries.',
  },
];

const fadein = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } };

export default function LandingPage() {
  return (
    <div className="space-y-16 sm:space-y-24">
      {/* ── 1. Hero Section ── */}
      <section className="relative overflow-hidden px-4 sm:px-6 pt-16 pb-20 sm:pt-24 sm:pb-28">
        {/* Subtle grid background */}
        <div
          className="absolute inset-0 opacity-[0.03] pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, var(--color-border-emphasis) 1px, transparent 0)',
            backgroundSize: '24px 24px',
          }}
        />
        {/* Ambient glow accent */}
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[140px] pointer-events-none" />

        <div className="relative max-w-6xl mx-auto grid lg:grid-cols-[1.1fr_0.9fr] gap-12 lg:gap-8 items-center">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={{ visible: { transition: { staggerChildren: 0.08 } } }}
            className="space-y-6 text-left"
          >
            <motion.div variants={fadein} className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="font-mono text-xs px-2.5 py-1 border-primary/30 text-primary">
                <span className="h-1.5 w-1.5 rounded-full bg-primary mr-1.5 animate-pulse" />
                Multi-Model Neural Network Ensemble
              </Badge>
              <Badge variant="secondary" className="text-xs">
                Research &amp; Educational Use
              </Badge>
            </motion.div>

            <motion.h1
              variants={fadein}
              className="text-4xl sm:text-5xl lg:text-6xl font-bold font-display leading-[1.08] tracking-tight text-text-primary"
            >
              Precision Histopathology<br />
              <span className="text-primary">Classified by Ensemble AI</span>
            </motion.h1>

            <motion.p variants={fadein} className="text-base sm:text-lg text-text-secondary max-w-xl leading-relaxed">
              OncoVision AI orchestrates a synchronized 3-model deep learning ensemble to evaluate lung and colon
              tissue slides with per-model consensus, transparent confidence metrics, and clinical decision support context.
            </motion.p>

            {/* Hero CTAs */}
            <motion.div variants={fadein} className="flex flex-wrap items-center gap-3 pt-2">
              <Button size="lg" asChild className="h-11 px-6 text-sm font-semibold shadow-md shadow-primary/20 gap-2 group">
                <Link to={ROUTES.REGISTER}>
                  <span>Start classifying</span>
                  <ArrowRight className="h-4 w-4 shrink-0 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild className="h-11 px-5 text-sm font-medium border-border hover:bg-surface-raised">
                <Link to={ROUTES.LOGIN}>
                  Sign in
                </Link>
              </Button>
            </motion.div>

            {/* Quick Metrics */}
            <motion.div variants={fadein} className="flex flex-wrap items-center gap-6 pt-4 border-t border-border-subtle text-xs font-mono">
              <div>
                <span className="text-text-primary font-bold text-base block tabular-nums">3 Models</span>
                <span className="text-text-muted">Ensemble Voting</span>
              </div>
              <div className="h-7 w-px bg-border-subtle" />
              <div>
                <span className="text-text-primary font-bold text-base block tabular-nums">5 Classes</span>
                <span className="text-text-muted">Lung &amp; Colon</span>
              </div>
              <div className="h-7 w-px bg-border-subtle" />
              <div>
                <span className="text-text-primary font-bold text-base block">WSI &amp; Tiles</span>
                <span className="text-text-muted">JPEG · PNG · TIFF</span>
              </div>
            </motion.div>
          </motion.div>

          {/* Hero Diagnostic Card Mockup */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="relative"
          >
            <Card className="p-6 space-y-5 border-border-emphasis bg-surface shadow-xl relative overflow-hidden backdrop-blur-sm">
              <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                <div className="flex items-center gap-2">
                  <Microscope className="h-4 w-4 text-primary" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-text-muted font-mono">
                    Sample Histopathology Finding
                  </span>
                </div>
                <Badge variant="lungAca" className="text-xs">
                  Lung Adenocarcinoma
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 rounded-lg bg-surface-raised/60 border border-border-subtle space-y-0.5">
                  <span className="text-[10px] text-text-muted uppercase block">Confidence</span>
                  <span className="text-lg font-bold text-text-primary tabular-nums">98.6%</span>
                  <span className="text-[10px] text-text-muted block">Ensemble weighted</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-raised/60 border border-border-subtle space-y-0.5">
                  <span className="text-[10px] text-text-muted uppercase block">Concordance</span>
                  <span className="text-lg font-bold text-text-secondary tabular-nums">100%</span>
                  <span className="text-[10px] text-text-muted block">3 of 3 models agreed</span>
                </div>
              </div>

              {/* Model execution status chips */}
              <div className="space-y-2 pt-1">
                <span className="text-[10px] uppercase tracking-wider font-mono text-text-muted block">
                  Constituent Estimators
                </span>
                <div className="space-y-1.5">
                  {MODELS.map((m) => (
                    <div key={m.name} className="flex items-center justify-between p-2 rounded bg-surface-raised/40 border border-border-subtle text-xs">
                      <div className="flex items-center gap-2 truncate">
                        <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
                        <span className="font-mono font-medium text-text-primary truncate">{m.name}</span>
                      </div>
                      <span className="font-mono text-[10px] text-text-muted shrink-0">Weight: {m.weight}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* ── 2. Platform Features ── */}
      <section id="features" className="px-4 sm:px-6 py-12 border-t border-border">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-2 max-w-xl mx-auto">
            <Badge variant="outline" className="font-mono text-xs">Platform Architecture</Badge>
            <h2 className="text-2xl sm:text-3xl font-bold font-display tracking-tight text-text-primary">
              Built for Research Precision
            </h2>
            <p className="text-text-muted text-xs sm:text-sm leading-relaxed">
              Explore deep learning histopathology classification with transparent runtime telemetry and reproducible evidence.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
              >
                <Card className="p-5 space-y-3.5 h-full hover:border-primary/40 transition-colors flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
                      {f.icon}
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm text-text-primary">{f.title}</h3>
                      <p className="text-xs text-text-secondary mt-1 leading-relaxed">{f.description}</p>
                    </div>
                  </div>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. Workflow Steps ── */}
      <section id="workflow" className="px-4 sm:px-6 py-12 border-t border-border bg-surface-raised/20">
        <div className="max-w-5xl mx-auto space-y-12">
          <div className="text-center space-y-2 max-w-xl mx-auto">
            <Badge variant="outline" className="font-mono text-xs">Diagnostic Pipeline</Badge>
            <h2 className="text-2xl sm:text-3xl font-bold font-display tracking-tight text-text-primary">
              Three Steps to Classification
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {WORKFLOW_STEPS.map((s, i) => (
              <motion.div
                key={s.step}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <Card className="p-5 space-y-3 h-full bg-surface border-border">
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-xs font-bold font-mono">
                    {s.step}
                  </span>
                  <h3 className="font-semibold text-sm text-text-primary">{s.title}</h3>
                  <p className="text-xs text-text-secondary leading-relaxed">{s.description}</p>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 4. Technology Manifest ── */}
      <section id="technology" className="px-4 sm:px-6 py-12 border-t border-border">
        <div className="max-w-5xl mx-auto space-y-8">
          <div className="text-center space-y-2 max-w-xl mx-auto">
            <Badge variant="outline" className="font-mono text-xs">Engine Manifest</Badge>
            <h2 className="text-2xl sm:text-3xl font-bold font-display tracking-tight text-text-primary">
              Multi-Model AI Runtime
            </h2>
            <p className="text-text-muted text-xs sm:text-sm">
              Live neural network architectures registered within the inference pipeline.
            </p>
          </div>

          <div className="grid sm:grid-cols-3 gap-4">
            {MODELS.map((m) => (
              <div
                key={m.name}
                className="p-4 rounded-xl border border-border bg-surface space-y-2 hover:border-primary/40 transition-colors"
              >
                <div className="flex items-center gap-2 text-primary">
                  <Layers className="h-4 w-4" />
                  <span className="text-xs font-semibold font-mono uppercase tracking-wide">Model Node</span>
                </div>
                <h4 className="text-sm font-bold text-text-primary truncate" title={m.name}>{m.name}</h4>
                <p className="text-[11px] text-text-muted">{m.type}</p>
                <div className="pt-2 border-t border-border-subtle flex items-center justify-between text-[11px] font-mono">
                  <span className="text-text-muted">Weight Allocation</span>
                  <span className="font-semibold text-primary">{m.weight}</span>
                </div>
              </div>
            ))}
          </div>

          {/* ── 5. Prominent Bottom Call To Action (Section 3 Screenshot Fix) ── */}
          <div className="mt-14 relative overflow-hidden rounded-2xl border border-primary/30 bg-surface-raised/60 backdrop-blur-md p-8 sm:p-12 text-center shadow-lg space-y-6">
            <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-48 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

            <div className="space-y-2 max-w-xl mx-auto relative">
              <Badge variant="outline" className="font-mono text-xs px-2.5 py-1 border-primary/30 text-primary">
                Instant Research Access
              </Badge>
              <h3 className="font-bold text-2xl sm:text-3xl font-display tracking-tight text-text-primary pt-1">
                Ready to classify your first specimen?
              </h3>
              <p className="text-sm text-text-secondary leading-relaxed">
                Get started with an open research account and deploy multi-model ensemble classification on your tissue slides in minutes.
              </p>
            </div>

            {/* Action Buttons Group */}
            <div className="flex flex-wrap items-center justify-center gap-3 pt-1 relative">
              <Button size="lg" asChild className="h-11 px-7 text-sm font-semibold shadow-md shadow-primary/20 gap-2 group">
                <Link to={ROUTES.REGISTER}>
                  <span>Create free account</span>
                  <ArrowRight className="h-4 w-4 shrink-0 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild className="h-11 px-6 text-sm font-medium border-border hover:bg-surface-raised">
                <Link to={ROUTES.LOGIN}>
                  Sign in
                </Link>
              </Button>
            </div>

            <p className="text-[11px] font-mono text-text-muted pt-2 relative">
              Investigational Use Only · Designed for Research &amp; Academic Exploration
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
