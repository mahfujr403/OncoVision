import { useState, useCallback } from 'react';
import { useDebounce } from './useDebounce';
import { DEBOUNCE_MS } from '@/constants/app';

export function useSearch(delay = DEBOUNCE_MS) {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, delay);

  const handleSearch = useCallback((value: string) => setQuery(value), []);
  const clearSearch = useCallback(() => setQuery(''), []);

  return { query, debouncedQuery, handleSearch, clearSearch };
}
