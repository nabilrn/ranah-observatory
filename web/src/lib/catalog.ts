import type { Locale } from './i18n';

export type DatasetStatus = 'materialized' | 'building';

export type DatasetEntry = {
  id: string;
  category: 'Disaster' | 'Climate' | 'Population' | 'Economy' | 'Infrastructure' | 'Environment';
  title: Record<Locale, string>;
  description: Record<Locale, string>;
  source: string;
  period: string;
  geography: string;
  formats: string[];
  status: DatasetStatus;
  sourcePath: string;
};

export const datasets: DatasetEntry[] = [
  {
    id: 'bnpb-disaster-canonical-observations',
    category: 'Disaster',
    title: { id: 'Kejadian bencana BNPB — observasi kanonik', en: 'BNPB disaster events — canonical observations' },
    description: { id: 'Observasi kejadian bencana yang sudah dipetakan ke geografi Ranah Observatory dengan provenance terpisah.', en: 'Disaster-event observations mapped to Ranah Observatory geographies with separate provenance.' },
    source: 'BNPB / DIBI', period: '2024 (current canonical slice)', geography: 'Kabupaten/kota Sumatera Barat', formats: ['CSV'], status: 'materialized',
    sourcePath: 'data/processed/bnpb/disaster/bnpb-disaster-canonical-observations.csv'
  },
  {
    id: 'bnpb-disaster-provenance',
    category: 'Disaster',
    title: { id: 'Provenance kejadian bencana BNPB', en: 'BNPB disaster-event provenance' },
    description: { id: 'Jejak sumber dan metodologi yang menjelaskan dari mana observasi bencana berasal.', en: 'Source and methodology trail explaining where each disaster observation came from.' },
    source: 'BNPB / DIBI', period: '2024', geography: 'Kabupaten/kota Sumatera Barat', formats: ['CSV'], status: 'materialized',
    sourcePath: 'data/processed/bnpb/disaster/bnpb-disaster-canonical-provenance.csv'
  },
  {
    id: 'chirps-annual-rainfall',
    category: 'Climate',
    title: { id: 'Curah hujan tahunan CHIRPS', en: 'CHIRPS annual rainfall' },
    description: { id: 'Konteks curah hujan berbasis grid untuk analisis iklim jangka panjang; bukan observasi stasiun BMKG.', en: 'Gridded rainfall context for long-run climate analysis; not direct BMKG station observations.' },
    source: 'CHIRPS v3', period: '1981–near present', geography: 'Grid / agregasi Sumatera Barat', formats: ['CSV'], status: 'materialized',
    sourcePath: 'data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv'
  },
  {
    id: 'bps-population-1961',
    category: 'Population',
    title: { id: 'Sensus Penduduk 1961 — data sumber', en: '1961 Population Census — source-native data' },
    description: { id: 'Ekstraksi historis dari publikasi sensus resmi dengan batas geografi historis tetap dipertahankan.', en: 'Historical extraction from the official census publication with historical geography limitations preserved.' },
    source: 'Biro Pusat Statistik', period: '1961', geography: 'Indonesia / Daerah Tingkat I', formats: ['CSV'], status: 'materialized',
    sourcePath: 'data/processed/bps/historical_population_1961_source_native.csv'
  },
  {
    id: 'bps-population-2000',
    category: 'Population',
    title: { id: 'Penduduk 2000 — data sumber historis', en: 'Population 2000 — historical source-native data' },
    description: { id: 'Data sumber historis yang dipertahankan sebelum penyelarasan geografi dan indikator.', en: 'Historical source-native data retained before geography and indicator harmonization.' },
    source: 'BPS', period: '2000', geography: 'Sumatera Barat', formats: ['CSV'], status: 'materialized',
    sourcePath: 'data/processed/bps/historical_population_2000_source_native.csv'
  },
  {
    id: 'bkpm-investment-history',
    category: 'Economy',
    title: { id: 'Riwayat investasi BKPM', en: 'BKPM investment history' },
    description: { id: 'Lane materialisasi investasi historis untuk membaca dinamika realisasi investasi.', en: 'Historical investment materialization lane for examining investment realization dynamics.' },
    source: 'BKPM', period: 'historical series', geography: 'Sumatera Barat / regional', formats: ['processed artifacts'], status: 'materialized',
    sourcePath: 'data/processed/bkpm/m27_full_history'
  },
  {
    id: 'sumbarprov-disaster-impact',
    category: 'Disaster',
    title: { id: 'Dampak bencana BPBD Sumbar', en: 'West Sumatra BPBD disaster impacts' },
    description: { id: 'Korban, permukiman, fasilitas umum, kejadian bulanan/kabupaten, dan kerugian yang sedang diambil dari portal Satu Data Sumbar.', en: 'Casualties, housing, public facilities, monthly/regency events, and losses being acquired from the West Sumatra open-data portal.' },
    source: 'BPBD Sumatera Barat / Satu Data Sumbar', period: '2023–2024 priority batch', geography: 'Kabupaten/kota Sumatera Barat', formats: ['XLSX'], status: 'building',
    sourcePath: 'data/acquisition_requests/sumbarprov_priority_datasets.csv'
  }
];

export const categoryLabels: Record<Locale, Record<DatasetEntry['category'], string>> = {
  id: { Disaster: 'Bencana', Climate: 'Iklim', Population: 'Penduduk', Economy: 'Ekonomi', Infrastructure: 'Infrastruktur', Environment: 'Lingkungan' },
  en: { Disaster: 'Disaster', Climate: 'Climate', Population: 'Population', Economy: 'Economy', Infrastructure: 'Infrastructure', Environment: 'Environment' }
};

export function repositoryUrl(path: string) {
  return `https://github.com/nabilrn/ranah-observatory/blob/main/${path}`;
}
