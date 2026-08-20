import type { ModelInfo, WorkflowStep } from './types';

export const ENSEMBLE_MODELS: ModelInfo[] = [
  { id: 'm1', name: 'ResNet50', version: 'v3.0.1', architecture: 'CNN', active: true },
  { id: 'm2', name: 'DenseNet121', version: 'v1.0.3', architecture: 'CNN', active: true },
  { id: 'm3', name: 'EfficientNetB4', version: 'v2.1.0', architecture: 'CNN', active: true },
  { id: 'm4', name: 'MobileNetV3', version: 'v1.1.0', architecture: 'CNN', active: true },
  { id: 'm5', name: 'VGG16', version: 'v1.0.0', architecture: 'CNN', active: true },
  { id: 'm6', name: 'ViT-B16', version: 'v1.2.0', architecture: 'Transformer', active: true },
];

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
    description: 'Six ensemble models run in parallel for independent classification.',
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
    label: 'Generate Report',
    description: 'A structured clinical report is produced and available for download.',
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
  { label: 'Maximum file size', value: '50 MB' },
  { label: 'Color mode', value: 'RGB (H&E stained)' },
  { label: 'Magnification', value: '10× – 40× preferred' },
] as const;
