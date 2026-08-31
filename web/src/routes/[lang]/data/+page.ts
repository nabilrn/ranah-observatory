import { base } from '$app/paths';
import type { PublicDataCatalog } from '$lib/catalog';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  const response = await fetch(`${base}/data/catalog.json`);
  if (!response.ok) throw new Error(`public data catalog fetch failed: ${response.status}`);
  const catalog = (await response.json()) as PublicDataCatalog;
  if (catalog.schema !== 'ranah-observatory/public-data-catalog/v1') {
    throw new Error(`unsupported public data catalog schema: ${catalog.schema}`);
  }
  return { catalog };
};
