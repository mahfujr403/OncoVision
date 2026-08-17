import type { WorkflowStep } from './types';

export const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    step: 1,
    label: 'Upload Image',
    description: 'Select a histopathology slide in JPEG, PNG, or TIFF format.',
    icon: 'upload',
  },
  {
    step: 2,
    label: 'AI Processing',
    description: 'Each available model runs inference in turn, producing an independent classification.',
    icon: 'cpu',
  },
  {
    step: 3,
    label: 'Ensemble Decision',
    description: 'Weighted voting produces a final label with calibrated confidence.',
    icon: 'git-merge',
  },
  {
    step: 4,
    label: 'Result & Report',
    description: 'Prediction result is saved to history. Structured report export is planned for a future release.',
    icon: 'file-text',
  },
];

export const SUPPORTED_FORMATS = [
  { ext: 'JPG', mime: 'image/jpeg', description: 'JPEG images' },
  { ext: 'JPEG', mime: 'image/jpeg', description: 'JPEG images' },
  { ext: 'PNG', mime: 'image/png', description: 'Portable Network Graphics' },
  { ext: 'TIFF', mime: 'image/tiff', description: 'Tagged Image File Format' },
] as const;

export const IMAGE_REQUIREMENTS = [
  { label: 'Recommended resolution', value: '≥ 224 × 224 px' },
  { label: 'Maximum file size', value: '10 MB' },
  { label: 'Color mode', value: 'RGB (H&E stained)' },
  { label: 'Magnification', value: '10× – 40× preferred' },
] as const;
