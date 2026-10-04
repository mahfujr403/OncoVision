import { useCallback, useMemo } from 'react';
import { useLocalStorage } from './useLocalStorage';

export interface ClinicalCase {
  id: string;
  image: string;
  label: string; // e.g. "lung_scc", "colon_aca", "lung_aca", "colon_benign", "lung_benign"
  confidence: number;
  agreementRatio?: number;
  participatingModels?: number;
  status: 'Completed' | 'Verified' | 'Flagged for Review';
  savedAt: string;
  isFavorite: boolean;
  note?: string;
  source: 'demo' | 'user';
}

export const INITIAL_CLINICAL_CASES: ClinicalCase[] = [
  {
    id: 'p7',
    image: 'rare_scc_case.tiff',
    label: 'lung_scc',
    confidence: 0.921,
    agreementRatio: 1.0,
    participatingModels: 3,
    status: 'Completed',
    savedAt: new Date(Date.now() - 86400000 * 2).toISOString(),
    isFavorite: false,
    note: 'Unusual keratinization morphology — flagged for MDT review',
    source: 'demo',
  },
  {
    id: 'p12',
    image: 'colon_aca_grade3.png',
    label: 'colon_aca',
    confidence: 0.964,
    agreementRatio: 0.75,
    participatingModels: 4,
    status: 'Flagged for Review',
    savedAt: new Date(Date.now() - 86400000 * 5).toISOString(),
    isFavorite: true,
    note: 'High-grade adenocarcinoma pattern, confirm with IHC staining',
    source: 'demo',
  },
  {
    id: 'p3',
    image: 'teaching_case_aca_1.tiff',
    label: 'lung_aca',
    confidence: 0.989,
    agreementRatio: 1.0,
    participatingModels: 3,
    status: 'Verified',
    savedAt: new Date(Date.now() - 86400000 * 1).toISOString(),
    isFavorite: true,
    note: 'Classic acinar predominant adenocarcinoma pattern',
    source: 'demo',
  },
  {
    id: 'p9',
    image: 'benchmark_colon_001.jpg',
    label: 'colon_benign',
    confidence: 0.978,
    agreementRatio: 1.0,
    participatingModels: 3,
    status: 'Completed',
    savedAt: new Date(Date.now() - 86400000 * 3).toISOString(),
    isFavorite: true,
    note: 'Normal colonic mucosa with preserved crypt architecture',
    source: 'demo',
  },
  {
    id: 'p14',
    image: 'atypical_scc_case.png',
    label: 'lung_scc',
    confidence: 0.903,
    agreementRatio: 0.67,
    participatingModels: 3,
    status: 'Flagged for Review',
    savedAt: new Date(Date.now() - 86400000 * 7).toISOString(),
    isFavorite: true,
    note: 'Poorly differentiated squamoid clusters; check p40 marker',
    source: 'demo',
  },
];

const STORAGE_KEY = 'oncovision_clinical_cases';

export function useClinicalCases() {
  const [cases, setCases, removeCases] = useLocalStorage<ClinicalCase[]>(
    STORAGE_KEY,
    INITIAL_CLINICAL_CASES,
  );

  const favoriteCases = useMemo(() => {
    return cases.filter((c) => c.isFavorite);
  }, [cases]);

  const toggleFavorite = useCallback(
    (caseId: string) => {
      setCases((prev) =>
        prev.map((c) => (c.id === caseId ? { ...c, isFavorite: !c.isFavorite } : c)),
      );
    },
    [setCases],
  );

  const removeCase = useCallback(
    (caseId: string) => {
      setCases((prev) => prev.filter((c) => c.id !== caseId));
    },
    [setCases],
  );

  const addCase = useCallback(
    (newCase: Omit<ClinicalCase, 'savedAt' | 'source'>) => {
      setCases((prev) => [
        {
          ...newCase,
          savedAt: new Date().toISOString(),
          source: 'user',
        },
        ...prev.filter((c) => c.id !== newCase.id),
      ]);
    },
    [setCases],
  );

  const updateNote = useCallback(
    (caseId: string, note: string) => {
      setCases((prev) =>
        prev.map((c) => (c.id === caseId ? { ...c, note } : c)),
      );
    },
    [setCases],
  );

  const resetToDefaults = useCallback(() => {
    removeCases();
  }, [removeCases]);

  return {
    cases,
    favoriteCases,
    toggleFavorite,
    removeCase,
    addCase,
    updateNote,
    resetToDefaults,
  };
}
