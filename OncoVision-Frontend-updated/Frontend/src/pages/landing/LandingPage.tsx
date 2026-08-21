import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Microscope, Brain, BarChart3, Shield, Zap, GitCompare,
  ArrowRight, ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ROUTES } from '@/constants/routes';

const FEATURES = [
  { icon: <Brain className="h-5 w-5" />, title: 'Ensemble AI', description: 'Three deep learning architectures combined via weighted voting.' },
  { icon: <Microscope className="h-5 w-5" />, title: 'Histopathology', description: 'Specialized for lung and colon cancer tissue analysis.' },
  { icon: <BarChart3 className="h-5 w-5" />, title: 'Analytics', description: 'Real prediction statistics — class distribution, confidence, and success rate.' },
  { icon: <Shield className="h-5 w-5" />, title: 'Research & Educational Use', description: 'Not clinically approved. Predictions may be inaccurate and must not be used for medical diagnosis.' },
  { icon: <Zap className="h-5 w-5" />, title: 'Fast Inference', description: 'Predictions with full confidence and model-agreement scoring.' },
  { icon: <GitCompare className="h-5 w-5" />, title: 'Prediction History', description: 'Every analysis saved with exportable CSV/PDF records.' },
];

// Real 3-model ensemble, verified against app/ml/manifest/models.json —
// not the 6 fabricated architectures previously listed here.
const MODELS = ['MobileNetV2', 'DenseNet121', 'EfficientNetV2B0 + ResNet50 Fusion'];

const WORKFLOW_STEPS = [
  { 
    step: '01',
    title: 'Upload Image',
    description: 'Drag and drop H&E stained histopathology images in JPEG or PNG format.' 
  },
  {
    step: '02',
    title: 'AI-Assisted Analysis',
    description:
      'Each available model analyzes the image independently and contributes to a weighted ensemble prediction, computed entirely server-side.',
  },
  {
    step: '03',
    title: 'Review Results',
    description:
      'View the predicted class, model confidence, and model agreement in your Prediction History, or export your data as CSV or PDF.',
  },
];

const fadein = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } };

export default function LandingPage() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden px-6 py-24 md:py-36">
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, var(--border) 1px, transparent 0)',
            backgroundSize: '28px 28px',
          }}
        />
        <div className="absolute top-0 right-0 w-2/3 h-2/3 bg-primary/5 rounded-full blur-[120px] pointer-events-none" />

        <div className="relative max-w-4xl mx-auto">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={{ visible: { transition: { staggerChildren: 0.08 } } }}
            className="space-y-6"
          >
            <motion.div variants={fadein}>
              <Badge variant="info" dot>
                Ensemble Deep Learning · Research & Educational Use
              </Badge>
            </motion.div>

            <motion.h1
              variants={fadein}
              className="text-4xl md:text-6xl font-bold font-display leading-[1.08] tracking-tight"
            >
              Cancer Histopathology<br />
              <span className="text-primary">Classified by AI</span>
            </motion.h1>

            <motion.p variants={fadein} className="text-base md:text-lg text-muted-foreground max-w-2xl leading-relaxed">
              OncoVision AI combines three deep learning models in a weighted ensemble to
              classify lung and colon cancer from histopathology images — with per-model
              confidence and agreement scoring on every prediction.
            </motion.p>

            <motion.div variants={fadein} className="flex flex-wrap items-center gap-3">
              <Button size="lg" asChild>
                <Link to={ROUTES.REGISTER}>
                  Start classifying <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link to={ROUTES.LOGIN}>Sign in</Link>
              </Button>
            </motion.div>

            <motion.div variants={fadein} className="flex flex-wrap gap-4 pt-2">
              {[{ v: 'Three', l: 'Models' }, { v: 'Five', l: 'Cancer Types' }, { v: 'JPEG · PNG ', l: 'Formats' }].map((s) => (
                <div key={s.l} className="flex items-center gap-2">
                  <span className="font-mono font-bold text-primary text-lg">{s.v}</span>
                  <span className="text-lg font-bold text-muted-foreground">{s.l}</span>
                </div>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 py-20 border-t border-border">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12 space-y-2">
            <Badge variant="secondary">Platform Features</Badge>
            <h2 className="text-3xl font-bold font-display">Built for Research Precision</h2>
            <p className="text-muted-foreground text-sm max-w-lg mx-auto">
              A research-oriented AI platform for exploring histopathology classification —
              not a diagnostic or clinically validated tool.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="rounded-lg border border-border bg-card p-5 space-y-3 hover:border-primary/30 transition-colors"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  {f.icon}
                </div>
                <div>
                  <h3 className="font-semibold text-sm">{f.title}</h3>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{f.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section id="workflow" className="px-6 py-20 border-t border-border bg-card/30">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12 space-y-2">
            <Badge variant="secondary">How it Works</Badge>
            <h2 className="text-3xl font-bold font-display">Three Steps to Classification</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {WORKFLOW_STEPS.map((s, i) => (
              <motion.div
                key={s.step}
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="relative space-y-3"
              >
                {i < WORKFLOW_STEPS.length - 1 && (
                  <div className="hidden md:block absolute top-4 left-full w-full h-px bg-border" />
                )}
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold font-mono">
                  {s.step}
                </span>
                <h3 className="font-semibold text-sm">{s.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{s.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology */}
      <section id="technology" className="px-6 py-20 border-t border-border">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12 space-y-2">
            <Badge variant="secondary">Technology</Badge>
            <h2 className="text-3xl font-bold font-display">Three Models, One Decision</h2>
            <p className="text-sm text-muted-foreground max-w-lg mx-auto">
              Ensemble learning combines independent predictions for robust, trustworthy classification.
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-3">
            {MODELS.map((m, i) => (
              <motion.div
                key={m}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className="rounded-full border border-border bg-card px-4 py-2 text-sm font-mono font-medium text-primary hover:border-primary/50 transition-colors"
              >
                {m}
              </motion.div>
            ))}
          </div>

          <div className="mt-12 rounded-xl border border-border bg-card/60 p-6 text-center space-y-4">
            <h3 className="font-semibold text-lg font-display">Ready to try it?</h3>
            <p className="text-sm text-muted-foreground">
              Get started with a free research account and classify your first histopathology slide in minutes.
            </p>
            <Button asChild>
              <Link to={ROUTES.REGISTER}>
                Create account <ChevronRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
