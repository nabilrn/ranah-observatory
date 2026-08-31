export const locales = ['id', 'en'] as const;
export type Locale = (typeof locales)[number];

export function isLocale(value: string): value is Locale {
  return locales.includes(value as Locale);
}

export function numberFormatter(locale: Locale, options: Intl.NumberFormatOptions = {}) {
  return new Intl.NumberFormat(locale === 'id' ? 'id-ID' : 'en-US', options);
}

export function currencyFormatter(locale: Locale, currency = 'IDR') {
  return new Intl.NumberFormat(locale === 'id' ? 'id-ID' : 'en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0
  });
}

export const copy = {
  id: {
    nav: { explore: 'Explore', data: 'Data Catalog', about: 'Tentang & metode' },
    brandSub: 'Sumatera Barat dalam data',
    switchLanguage: 'English',
    home: {
      eyebrow: 'Observatorium data Sumatera Barat',
      title: 'Lihat apa yang terjadi, kenapa penting, dan apa yang mungkin terjadi berikutnya.',
      lead: 'Ranah Observatory menghubungkan data resmi lintas sektor agar kondisi, ketertinggalan, risiko, dan potensi Sumatera Barat dapat diperiksa tanpa harus membaca tumpukan laporan teknis.',
      note: 'Setiap temuan publik harus dapat ditelusuri kembali ke dataset, periode, wilayah, dan sumbernya.',
      exploreTitle: 'Mulai dari pertanyaan, bukan dari file data',
      exploreText: 'Vertical pertama yang sedang diselesaikan adalah bencana. Struktur yang sama kemudian dipakai untuk ekonomi, infrastruktur, tenaga kerja, pendidikan, kesehatan, dan lingkungan.',
      investorTitle: 'Bisa dipakai untuk membaca konteks investasi',
      investorText: 'Investor dapat membandingkan wilayah menggunakan ekonomi, tenaga kerja, konektivitas, layanan dasar, dan exposure risiko dari fondasi data yang sama—tanpa skor buatan yang tidak dapat dipertanggungjawabkan.'
    },
    disaster: {
      eyebrow: 'Explore · Bencana',
      title: 'Bencana di Sumatera Barat',
      lead: 'Telusuri kejadian, dampak, wilayah, faktor terkait, dan bukti sumber. Angka dampak baru akan ditampilkan setelah dataset BPBD/BNPB selesai dimaterialisasi dan lolos validasi.',
      mapTitle: 'Sebaran kabupaten/kota',
      mapPending: 'Layer geospasial publik sedang disiapkan. MapLibre akan membaca GeoJSON/PMTiles hasil public build, bukan file analisis mentah.',
      proofTitle: 'Rantai bukti',
      contextTitle: 'Data yang sedang dilengkapi'
    },
    catalog: {
      eyebrow: 'Data Catalog',
      title: 'Dataset yang menopang Ranah Observatory',
      lead: 'Katalog ini berorientasi dataset, bukan daftar indikator riset. Cari berdasarkan sektor, sumber, periode, atau wilayah.',
      search: 'Cari dataset atau sumber…',
      all: 'Semua sektor',
      period: 'Periode',
      geography: 'Wilayah',
      source: 'Sumber',
      status: 'Status',
      materialized: 'Siap digunakan',
      building: 'Sedang dilengkapi',
      empty: 'Tidak ada dataset yang cocok.'
    },
    about: {
      eyebrow: 'Tentang & metode',
      title: 'Kerumitan riset tetap di belakang layar.',
      lead: 'Produk publik menggunakan bahasa sederhana, sementara provenance, validasi, batas metodologi, dan artefak penelitian tetap tersedia untuk pemeriksaan.',
      principles: ['Sumber resmi diprioritaskan', 'Klaim harus kembali ke data', 'Observasi dan estimasi dibedakan', 'Ketidakpastian tidak disembunyikan', 'Tidak membuat angka potensi tanpa dasar defensible']
    }
  },
  en: {
    nav: { explore: 'Explore', data: 'Data Catalog', about: 'About & methodology' },
    brandSub: 'West Sumatra in data',
    switchLanguage: 'Bahasa Indonesia',
    home: {
      eyebrow: 'West Sumatra data observatory',
      title: 'See what is happening, why it matters, and what may happen next.',
      lead: 'Ranah Observatory connects official cross-sector data so West Sumatra’s conditions, development gaps, risks, and opportunities can be examined without reading stacks of technical reports.',
      note: 'Every public finding must be traceable to its dataset, period, geography, and source.',
      exploreTitle: 'Start with questions, not files',
      exploreText: 'Disaster is the first vertical being completed. The same structure will then extend to the economy, infrastructure, labor, education, health, and environment.',
      investorTitle: 'Useful for investment context',
      investorText: 'Investors can compare locations using economic activity, labor, connectivity, basic services, and risk exposure from the same evidence base—without arbitrary black-box scores.'
    },
    disaster: {
      eyebrow: 'Explore · Disaster',
      title: 'Disasters in West Sumatra',
      lead: 'Explore events, impacts, locations, related factors, and source evidence. Impact figures are held until BPBD/BNPB datasets are materialized and validated.',
      mapTitle: 'Regency/city distribution',
      mapPending: 'The public geospatial layer is being prepared. MapLibre will consume GeoJSON/PMTiles from the public build, not raw research files.',
      proofTitle: 'Evidence chain',
      contextTitle: 'Data being completed'
    },
    catalog: {
      eyebrow: 'Data Catalog',
      title: 'Datasets supporting Ranah Observatory',
      lead: 'This catalog is dataset-centric rather than a list of research indicators. Search by sector, source, period, or geography.',
      search: 'Search dataset or source…',
      all: 'All sectors',
      period: 'Period',
      geography: 'Geography',
      source: 'Source',
      status: 'Status',
      materialized: 'Ready to use',
      building: 'Being completed',
      empty: 'No matching datasets.'
    },
    about: {
      eyebrow: 'About & methodology',
      title: 'Research complexity stays behind the interface.',
      lead: 'The public product uses plain language while provenance, validation, methodological boundaries, and research artifacts remain available for inspection.',
      principles: ['Prioritize official sources', 'Claims must trace back to data', 'Separate observations from estimates', 'Do not hide uncertainty', 'Do not invent potential estimates without defensible evidence']
    }
  }
} as const;
