<script lang="ts">
  import { onMount } from 'svelte';
  import type { DisasterDistrictRow, PublicDistrictBoundary } from '$lib/public-data';
  import type { Map as MapLibreMap } from 'maplibre-gl';

  type MutableGeoJsonSource = {
    setData: (data: unknown) => void;
  };

  export let geography: PublicDistrictBoundary;
  export let rows: DisasterDistrictRow[];
  export let indicators: string[];
  export let selectedGeographyId = 'all';
  export let selectGeography: (geographyId: string) => void = () => {};
  export let lang: 'id' | 'en' = 'id';

  let container: HTMLDivElement;
  let map: MapLibreMap | undefined;
  let loaded = false;
  let hoveredName = '';
  let hoveredValue: number | undefined;

  function valueByGeography() {
    const result = new Map<string, number>();
    for (const row of rows) {
      result.set(
        row.geography_id,
        indicators.reduce((total, indicator) => total + (row.values[indicator] ?? 0), 0)
      );
    }
    return result;
  }

  function decoratedGeojson() {
    const values = valueByGeography();
    return {
      ...geography,
      features: geography.features.map((feature) => ({
        ...feature,
        properties: {
          ...feature.properties,
          event_value: values.get(feature.properties.geography_id) ?? 0
        }
      }))
    };
  }

  function coordinateBounds() {
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    function walk(value: unknown) {
      if (!Array.isArray(value)) return;
      if (
        value.length >= 2 &&
        typeof value[0] === 'number' &&
        typeof value[1] === 'number'
      ) {
        minX = Math.min(minX, value[0]);
        minY = Math.min(minY, value[1]);
        maxX = Math.max(maxX, value[0]);
        maxY = Math.max(maxY, value[1]);
        return;
      }
      for (const child of value) walk(child);
    }

    for (const feature of geography.features) walk(feature.geometry?.coordinates);
    if (![minX, minY, maxX, maxY].every(Number.isFinite)) return undefined;
    return [[minX, minY], [maxX, maxY]] as [[number, number], [number, number]];
  }

  function refreshMap() {
    if (!map || !loaded) return;
    const data = decoratedGeojson();
    const source = map.getSource('districts') as MutableGeoJsonSource | undefined;
    source?.setData(data);

    const maximum = Math.max(
      1,
      ...data.features.map((feature) => Number(feature.properties.event_value ?? 0))
    );
    map.setPaintProperty('district-fill', 'fill-color', [
      'interpolate',
      ['linear'],
      ['get', 'event_value'],
      0,
      '#f4f4ef',
      maximum,
      '#161616'
    ]);
    map.setFilter(
      'district-selected',
      ['==', ['get', 'geography_id'], selectedGeographyId === 'all' ? '__none__' : selectedGeographyId]
    );
  }

  $: rows, indicators, selectedGeographyId, refreshMap();

  onMount(() => {
    let destroyed = false;

    async function initialize() {
      const { Map } = await import('maplibre-gl');
      if (destroyed) return;
      const initialData = decoratedGeojson();
      const maximum = Math.max(
        1,
        ...initialData.features.map((feature) => Number(feature.properties.event_value ?? 0))
      );
      const bounds = coordinateBounds();

      map = new Map({
        container,
        attributionControl: false,
        style: {
          version: 8,
          sources: {
            districts: {
              type: 'geojson',
              data: initialData as never
            }
          },
          layers: [
            {
              id: 'background',
              type: 'background',
              paint: { 'background-color': '#ecece7' }
            },
            {
              id: 'district-fill',
              type: 'fill',
              source: 'districts',
              paint: {
                'fill-color': [
                  'interpolate',
                  ['linear'],
                  ['get', 'event_value'],
                  0,
                  '#f4f4ef',
                  maximum,
                  '#161616'
                ],
                'fill-opacity': 0.88
              }
            },
            {
              id: 'district-outline',
              type: 'line',
              source: 'districts',
              paint: { 'line-color': '#ffffff', 'line-width': 0.8, 'line-opacity': 0.9 }
            },
            {
              id: 'district-selected',
              type: 'line',
              source: 'districts',
              filter: ['==', ['get', 'geography_id'], '__none__'],
              paint: { 'line-color': '#111111', 'line-width': 3 }
            }
          ]
        } as never,
        ...(bounds ? { bounds, fitBoundsOptions: { padding: 28, duration: 0 } } : { center: [100.45, -0.75], zoom: 5.7 })
      });

      map.on('load', () => {
        loaded = true;
        refreshMap();
      });

      map.on('mousemove', 'district-fill', (event) => {
        const feature = event.features?.[0];
        if (!feature) return;
        map!.getCanvas().style.cursor = 'pointer';
        hoveredName = String(feature.properties?.name ?? '');
        const rawValue = Number(feature.properties?.event_value);
        hoveredValue = Number.isFinite(rawValue) ? rawValue : undefined;
      });

      map.on('mouseleave', 'district-fill', () => {
        map!.getCanvas().style.cursor = '';
        hoveredName = '';
        hoveredValue = undefined;
      });

      map.on('click', 'district-fill', (event) => {
        const geographyId = String(event.features?.[0]?.properties?.geography_id ?? '');
        if (geographyId) selectGeography(geographyId);
      });
    }

    initialize();
    return () => {
      destroyed = true;
      map?.remove();
      map = undefined;
      loaded = false;
    };
  });
</script>

<div class="disaster-map-wrap">
  <div class="disaster-map" bind:this={container} aria-label={lang === 'id' ? 'Peta kejadian bencana Sumatera Barat' : 'West Sumatra disaster event map'}></div>
  <div class="map-legend" aria-hidden="true">
    <span>{lang === 'id' ? 'Lebih sedikit' : 'Fewer'}</span>
    <i></i>
    <span>{lang === 'id' ? 'Lebih banyak' : 'More'}</span>
  </div>
  <div class="map-readout" aria-live="polite">
    {#if hoveredName}
      <strong>{hoveredName}</strong>
      <span>{hoveredValue?.toLocaleString(lang === 'id' ? 'id-ID' : 'en-US') ?? '—'} {lang === 'id' ? 'kejadian terfilter' : 'filtered events'}</span>
    {:else}
      <strong>{lang === 'id' ? 'Arahkan atau klik wilayah' : 'Hover or click a region'}</strong>
      <span>{lang === 'id' ? 'Klik untuk memakai wilayah sebagai filter.' : 'Click to use the region as the active filter.'}</span>
    {/if}
  </div>
</div>
