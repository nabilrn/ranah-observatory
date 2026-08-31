import type { Locale } from './i18n';

export type DatasetStatus = 'materialized' | 'building';
export type DatasetCategory = 'Disaster' | 'Climate' | 'Population' | 'Economy' | 'Infrastructure' | 'Environment';

export type DatasetEntry = {
  id: string;
  category: DatasetCategory;
  title: Record<Locale, string>;
  description: Record<Locale, string>;
  source: string;
  period: string;
  geography: string;
  formats: string[];
  status: DatasetStatus;
  source_path: string;
  source_path_type: 'file' | 'directory';
};

export type PublicDataCatalog = {
  schema: 'ranah-observatory/public-data-catalog/v1';
  source: { path: string; sha256: string };
  summary: {
    dataset_count: number;
    materialized_count: number;
    building_count: number;
    category_count: number;
  };
  categories: DatasetCategory[];
  datasets: DatasetEntry[];
};

export const categoryLabels: Record<Locale, Record<DatasetCategory, string>> = {
  id: { Disaster: 'Bencana', Climate: 'Iklim', Population: 'Penduduk', Economy: 'Ekonomi', Infrastructure: 'Infrastruktur', Environment: 'Lingkungan' },
  en: { Disaster: 'Disaster', Climate: 'Climate', Population: 'Population', Economy: 'Economy', Infrastructure: 'Infrastructure', Environment: 'Environment' }
};

export function repositoryUrl(path: string) {
  const encodedPath = path.split('/').map(encodeURIComponent).join('/');
  return `https://github.com/nabilrn/ranah-observatory/blob/main/${encodedPath}`;
}
