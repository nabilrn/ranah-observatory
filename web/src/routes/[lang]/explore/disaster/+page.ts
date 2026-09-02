import { base } from '$app/paths';
import type { PublicDisasterSummary, PublicDistrictBoundary } from '$lib/public-data';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  const [summaryResponse, geographyResponse] = await Promise.all([
    fetch(`${base}/data/disaster-summary.json`),
    fetch(`${base}/data/sumbar-kabkota.geojson`)
  ]);
  if (!summaryResponse.ok) throw new Error(`public disaster summary fetch failed: ${summaryResponse.status}`);
  if (!geographyResponse.ok) throw new Error(`public geography fetch failed: ${geographyResponse.status}`);

  const summary = (await summaryResponse.json()) as PublicDisasterSummary;
  const geography = (await geographyResponse.json()) as PublicDistrictBoundary;
  if (summary.schema !== 'ranah-observatory/public-disaster-summary/v4') {
    throw new Error(`unsupported public disaster summary schema: ${summary.schema}`);
  }
  if (geography.type !== 'FeatureCollection' || geography.features.length !== summary.geography.feature_count) {
    throw new Error('public geography contract does not match disaster summary metadata');
  }
  return { summary, geography };
};
