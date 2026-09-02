# Milestone 64 — KRB Sumatera Barat 2022–2026: Rekomendasi Mitigasi per Ancaman

## Tujuan

M64 menambahkan layer resmi untuk menjawab pertanyaan produk **“apa tindakan mitigasi yang direkomendasikan untuk jenis ancaman ini?”** tanpa mengubah rekomendasi kebijakan menjadi bukti implementasi, probabilitas kejadian, atau proyeksi kerugian.

Sumber utama adalah **Kajian Risiko Bencana Provinsi Sumatera Barat 2022–2026** yang dipublikasikan BNPB/InaRISK.

## Sumber dan akuisisi

PDF resmi berukuran sekitar 17,2 MB tidak diduplikasi ke git. Akuisisi membekukan:

- URL resmi;
- SHA256 PDF asli `58e18cbc8457dc8a6f47fd3e094b8b23358966b2dba8dfae67eff05d385fddd4`;
- ukuran byte;
- excerpt pencarian non-OCR;
- excerpt reading-order non-OCR physical PDF pages 98–109.

Raw PDF diverifikasi ulang terhadap SHA256 yang sama saat membangun reading-order excerpt. Jika file upstream berubah, acquisition harus gagal alih-alih mencampur dua versi publikasi.

## Kenapa `pdftotext -layout` tidak dipakai sebagai canonical parser

Eksperimen awal menunjukkan halaman rekomendasi memiliki tata letak yang dapat membuat `pdftotext -layout` menginterleave dua kolom. Contohnya isi rekomendasi satu ancaman dapat tercampur dengan blok lain pada halaman yang sama.

Karena itu M64 secara eksplisit menetapkan:

- `layout_excerpt_authorized_for_section_materialization=false`;
- `reading_order_excerpt_authorized_for_section_materialization=true`;
- materialisasi canonical menggunakan `pdftotext -raw` pada physical PDF pages 98–109;
- OCR tidak digunakan.

Ini merupakan boundary kualitas data, bukan sekadar pilihan formatting.

## Coverage section rekomendasi

M64 mempertahankan 14 section spesifik KRB:

1. Banjir
2. Banjir Bandang
3. Cuaca Ekstrim
4. Gelombang Ekstrim dan Abrasi
5. Gempabumi
6. Likuefaksi
7. Kebakaran Hutan dan Lahan
8. Kekeringan
9. Letusan Gunungapi
10. Tanah Longsor
11. Tsunami
12. Epidemi dan Wabah Penyakit
13. Kegagalan Teknologi
14. COVID-19

Setiap section memiliki `krb_hazard_id` lokal dan label sumber asli. M64 **tidak** mengotorisasi equivalence otomatis dengan taxonomy IRBI, BPBD/Pusdalops, atau BNPB event observations.

## Layer aksi dashboard

Untuk 11 section yang sumbernya memakai daftar aksi top-level linear, M64 mengekstrak aksi secara deterministik. Totalnya **60 rekomendasi**:

| Ancaman | Jumlah aksi |
| --- | ---: |
| Banjir | 7 |
| Banjir Bandang | 6 |
| Cuaca Ekstrim | 6 |
| Gelombang Ekstrim dan Abrasi | 6 |
| Gempabumi | 2 |
| Likuefaksi | 5 |
| Kebakaran Hutan dan Lahan | 4 |
| Kekeringan | 5 |
| Letusan Gunungapi | 7 |
| Tanah Longsor | 4 |
| Tsunami | 8 |
| **Total** | **60** |

Contoh tindakan yang sekarang dapat disajikan langsung oleh produk antara lain penataan ruang dan jalur evakuasi untuk banjir, mitigasi struktural DAS, sistem peringatan dini, rekayasa konstruksi tahan gempa, rehabilitasi fungsi hutan, penguatan PRBBK untuk gunungapi, serta penyediaan TES dan rambu tsunami.

Teks aksi tetap source-native. Hanya page furniture seperti header publikasi yang dihapus dari kolom aksi agar tabel publik bersih; halaman sumber tetap disimpan sebagai `start_pdf_page` dan `end_pdf_page`.

## Section nested yang tidak di-flatten

Tiga section memiliki struktur internal bertingkat dan numbered lists yang restart:

- Epidemi dan Wabah Penyakit;
- Kegagalan Teknologi;
- COVID-19.

M64 tidak memaksa ketiganya menjadi flat action list karena itu akan menciptakan hierarchy yang tidak dinyatakan sumber. Statusnya adalah:

`source_section_only_nested_structure`

Isi lengkapnya tetap tersedia pada source-native recommendation section dataset. Dengan demikian tidak ada kehilangan evidence; yang dibatasi hanya transformasi yang tidak aman.

## Interpretasi yang diizinkan

Dashboard boleh menyatakan bahwa KRB BNPB **merekomendasikan** tindakan tertentu untuk suatu ancaman dan boleh menunjukkan konteks prioritas/ruang lingkup yang tertulis pada section tersebut.

Dashboard tidak boleh menyatakan bahwa:

- rekomendasi tersebut sudah dilaksanakan;
- rekomendasi tersebut terbukti efektif di Sumatera Barat tanpa evidence outcome terpisah;
- tidak menjalankan rekomendasi akan menyebabkan probabilitas atau nilai kerugian tertentu;
- urutan daftar rekomendasi adalah ranking efektivitas;
- taxonomy KRB identik dengan taxonomy IRBI atau BPBD tanpa crosswalk eksplisit.

Karena itu seluruh action rows memiliki:

- `claim_type=official_risk_reduction_recommendation`;
- `observed_implementation_claimed=false`;
- `prediction_claim_authorized=false`;
- `unmitigated_loss_forecast_authorized=false`.

## Output

- `data/processed/bnpb/krb_sumbar_2022_2026/krb-specific-recommendation-sections.csv`
- `data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-mitigation-actions-2022-2026.csv`
- `data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-recommendation-context-2022-2026.csv`
- `data/manifests/milestone64_krb_recommendations_acquisition.json`
- `data/manifests/milestone64_krb_recommendations_final.json`

Public catalog mempromosikan action table sebagai layer konsumsi utama dan source-native section table sebagai proof/audit layer.

## Product contract

Dengan M61–M64, produk kini dapat memisahkan empat konsep yang sebelumnya mudah tercampur:

1. **Apa yang terjadi?** — event/impact BPBD/BNPB.
2. **Seberapa besar risikonya?** — IRBI BNPB.
3. **Apa gap/target institusionalnya?** — Renja BPBD 2026.
4. **Apa tindakan mitigasi yang direkomendasikan untuk ancaman tersebut?** — KRB BNPB 2022–2026.

M64 belum mengotorisasi klaim “apa yang pasti terjadi jika tidak dimitigasi”. Klaim seperti itu membutuhkan model atau evidence kausal/forecast terpisah dan tidak boleh diinferensikan hanya dari rekomendasi KRB.
