export type DisasterAnnualTotal = {
  year: number;
  indicator_id: string;
  value: number;
  unit: 'count';
};

export type DisasterDistrictRow = {
  year: number;
  geography_id: string;
  name: string;
  values: Record<string, number>;
};

export type PublicDisasterSummary = {
  schema: 'ranah-observatory/public-disaster-summary/v1';
  source: {
    organization: string;
    path: string;
    sha256: string;
    row_count_used: number;
  };
  years: number[];
  indicators: string[];
  annual_totals: DisasterAnnualTotal[];
  district_rows: DisasterDistrictRow[];
  interpretation: { id: string; en: string };
  impact_values_included: false;
  missing_values_inferred: false;
};

export function eventLabel(indicator: string, lang: 'id' | 'en') {
  const labels: Record<string, { id: string; en: string }> = {
    flood_events: { id: 'Banjir', en: 'Flood' },
    landslide_events: { id: 'Tanah longsor', en: 'Landslide' }
  };
  return labels[indicator]?.[lang] ?? indicator.replaceAll('_', ' ');
}
