import { base } from '$app/paths';
import type { PublicDisasterSummary } from '$lib/public-data';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  const response = await fetch(`${base}/data/disaster-summary.json`);
  if (!response.ok) throw new Error(`public disaster summary fetch failed: ${response.status}`);
  const summary = (await response.json()) as PublicDisasterSummary;
  if (summary.schema !== 'ranah-observatory/public-disaster-summary/v1') {
    throw new Error(`unsupported public disaster summary schema: ${summary.schema}`);
  }
  return { summary };
};
