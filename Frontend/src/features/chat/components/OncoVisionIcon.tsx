import React from 'react';
import { Microscope } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface OncoVisionIconProps {
  className?: string;
  size?: number;
}

export const OncoVisionIcon: React.FC<OncoVisionIconProps> = ({ className = "w-4 h-4", size }) => {
  return (
    <Microscope
      className={cn("shrink-0", className)}
      size={size}
      aria-hidden="true"
    />
  );
};

export default OncoVisionIcon;
