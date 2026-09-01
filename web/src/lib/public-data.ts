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
  name?: string;
  values: Record<string, number>;
};

export type LossCoverageRow = {
  year: 2023;
  geography_id: string;
  name: string;
  disaster_events_reported: number;
  economic_loss_estimate_idr: number | null;
  loss_value_status: 'reported_numeric' | 'source_blank' | 'source_dash';
};

export type CasualtyByHazardRow = {
  year: 2024;
  hazard_id: string;
  source_hazard_label: string;
  indicator_id: string;
  value: number;
  unit: string;
};

export type MonthlyEventRow = {
  year: 2024;
  month: number;
  month_name_source: string;
  hazard_id: string;
  source_hazard_label: string;
  value: number | null;
  unit: string;
  source_blank: boolean;
};

export type EventSourceComparison = {
  bpbd_pusdalops_total: number;
  bnpb_canonical_total: number;
  difference_bpbd_minus_bnpb: number;
  status: 'match' | 'cross_source_divergent';
  interpretation: string;
};

export type TsunamiSirenRow = {
  siren_id: string;
  source_number: number;
  location_name: string;
  address: string;
  geography_id: string;
  name: string;
  ownership: string;
  installed_year: number;
  latitude: number;
  longitude: number;
  source_status: string;
  status: 'active' | 'inactive' | 'unknown';
  status_check_date: string;
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

type PublicImpactSummary = {
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

export type PublicDisasterSummary = {
  schema: 'ranah-observatory/public-disaster-summary/v3';
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
  impact_2024: PublicImpactSummary;
  impact_2023: PublicImpactSummary & {
    loss_coverage: LossCoverageRow[];
    economic_loss: {
      reported_total_idr: number;
      numeric_district_count: number;
      missing_district_count: number;
      district_count: number;
      coverage_complete: boolean;
    };
  };
  context_2024: {
    source: {
      organization: string;
      materialization_path: string;
      materialization_sha256: string;
      cross_source_policy: string;
    };
    monthly_events: {
      path: string;
      sha256: string;
      rows: MonthlyEventRow[];
      annual_total: number;
      hazard_totals: Record<string, number>;
      event_source_comparison: Record<string, EventSourceComparison>;
      interpretation: { id: string; en: string };
    };
    casualties_by_hazard: {
      path: string;
      sha256: string;
      rows: CasualtyByHazardRow[];
      totals: Record<string, number>;
    };
    tsunami_sirens: {
      path: string;
      sha256: string;
      rows: TsunamiSirenRow[];
      count: number;
      status_counts: Record<'active' | 'inactive' | 'unknown', number>;
      geography_count: number;
      interpretation: { id: string; en: string };
    };
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
  economic_loss_2023_included: true;
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

export function hazardLabel(hazard: string, lang: 'id' | 'en') {
  const labels: Record<string, { id: string; en: string }> = {
    flood: { id: 'Banjir', en: 'Flood' },
    extreme_weather: { id: 'Cuaca ekstrem', en: 'Extreme weather' },
    volcanic_eruption: { id: 'Erupsi gunung api', en: 'Volcanic eruption' },
    tidal_wave_and_coastal_erosion: { id: 'Gelombang pasang & abrasi', en: 'Tidal wave & coastal erosion' },
    forest_and_land_fire: { id: 'Kebakaran hutan & lahan', en: 'Forest & land fire' },
    drought: { id: 'Kekeringan', en: 'Drought' },
    landslide: { id: 'Tanah longsor', en: 'Landslide' }
  };
  return labels[hazard]?.[lang] ?? hazard.replaceAll('_', ' ');
}

export function impactLabel(indicator: string, lang: 'id' | 'en') {
  const labels: Record<string, { id: string; en: string }> = {
    disaster_events_reported: { id: 'Kejadian dilaporkan', en: 'Reported events' },
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
    bridges_affected: { id: 'Jembatan', en: 'Bridges' },
    economic_loss_estimate_idr: { id: 'Taksiran kerugian', en: 'Estimated losses' }
  };
  return labels[indicator]?.[lang] ?? indicator.replaceAll('_', ' ');
}
