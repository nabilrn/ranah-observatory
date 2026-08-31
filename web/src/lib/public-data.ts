export type DisasterAnnualTotal = {
  year: number;
  indicator_id: string;
  value: number;
  unit: string;
};

export type DisasterDistrictRow = {
  year: number;
  geography_id: string;
  name: string;
  values: Record<string, number>;
};

export type ImpactDistrictRow = {
  year: number;
  geography_id: string;
  values: Record<string, number>;
};

export type PublicBoundaryFeature = {
  type: 'Feature';
  geometry: {
    type: 'Polygon' | 'MultiPolygon';
    coordinates: unknown[];
  } | null;
  properties: {
    geography_id: string;
    name: string;
    source_name: string;
    source_code: string;
    mapping_method: 'kdpkab' | 'exact_source_name';
    province: string;
    source_feature_count: number;
  };
};

export type PublicDistrictBoundary = {
  type: 'FeatureCollection';
  name: string;
  features: PublicBoundaryFeature[];
};

export type PublicDisasterSummary = {
  schema: 'ranah-observatory/public-disaster-summary/v2';
  events: {
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
  };
  impact: {
    source: {
      organization: string;
      path: string;
      sha256: string;
      row_count_used: number;
      materialization_path: string;
    };
    years: number[];
    indicators: string[];
    indicator_units: Record<string, string>;
    annual_totals: DisasterAnnualTotal[];
    district_rows: ImpactDistrictRow[];
    interpretation: { id: string; en: string };
  };
  geography: {
    organization: string;
    path: string;
    sha256: string;
    crosswalk_path: string;
    crosswalk_sha256: string;
    feature_count: number;
    mapping_methods: Record<string, number>;
    public_path: string;
    anomaly_note: string;
  };
  impact_values_included: true;
  economic_loss_2024_included: false;
  missing_values_inferred: false;
};

export function eventLabel(indicator: string, lang: 'id' | 'en') {
  const labels: Record<string, { id: string; en: string }> = {
    flood_events: { id: 'Banjir', en: 'Flood' },
    landslide_events: { id: 'Tanah longsor', en: 'Landslide' }
  };
  return labels[indicator]?.[lang] ?? indicator.replaceAll('_', ' ');
}

export function impactLabel(indicator: string, lang: 'id' | 'en') {
  const labels: Record<string, { id: string; en: string }> = {
    deaths: { id: 'Meninggal', en: 'Deaths' },
    missing_people: { id: 'Hilang', en: 'Missing' },
    injured_or_sick_people: { id: 'Luka/sakit', en: 'Injured/sick' },
    suffering_people: { id: 'Menderita', en: 'Suffering' },
    displaced_people: { id: 'Mengungsi', en: 'Displaced' },
    houses_heavily_damaged: { id: 'Rumah rusak berat', en: 'Heavily damaged houses' },
    houses_moderately_damaged: { id: 'Rumah rusak sedang', en: 'Moderately damaged houses' },
    houses_lightly_damaged: { id: 'Rumah rusak ringan', en: 'Lightly damaged houses' },
    houses_flooded: { id: 'Rumah terendam', en: 'Flooded houses' },
    education_facilities_affected: { id: 'Fasilitas pendidikan', en: 'Education facilities' },
    worship_facilities_affected: { id: 'Fasilitas peribadatan', en: 'Worship facilities' },
    health_facilities_affected: { id: 'Fasilitas kesehatan', en: 'Health facilities' },
    office_facilities_affected: { id: 'Fasilitas kantor', en: 'Office facilities' },
    bridges_affected: { id: 'Jembatan', en: 'Bridges' }
  };
  return labels[indicator]?.[lang] ?? indicator.replaceAll('_', ' ');
}
