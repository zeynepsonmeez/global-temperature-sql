"""English / Turkish interface strings. English is the default language."""

from __future__ import annotations

import streamlit as st

LANGUAGES = {"EN": "en", "TR": "tr"}

TEXT: dict[str, dict[str, str]] = {
    # --- navigation / shared ---------------------------------------------------
    "nav.home":            {"en": "Home", "tr": "Ana Sayfa"},
    "nav.explorer":        {"en": "Climate Explorer", "tr": "Climate Explorer"},
    "nav.playground":      {"en": "SQL Playground", "tr": "SQL Playground"},
    "lang.label":          {"en": "Language", "tr": "Dil"},
    "sql.behind":          {"en": "SQL behind this chart", "tr": "Bu grafiğin SQL'i"},
    "sql.open":            {"en": "Open in Playground", "tr": "Playground'da aç"},
    "sql.download":        {"en": "Download CSV", "tr": "CSV indir"},
    "db.down":             {"en": "The database is not reachable. Start it with `docker compose up -d` and reload.",
                            "tr": "Veritabanına ulaşılamıyor. `docker compose up -d` ile başlatıp sayfayı yenileyin."},
    "footer.data":         {"en": "Data: NASA GISS Surface Temperature Analysis (GISTEMP v4). Anomalies in °C relative to 1951–1980.",
                            "tr": "Veri: NASA GISS Surface Temperature Analysis (GISTEMP v4). Anomaliler 1951–1980 ortalamasına göre °C."},
    "region.GLB":          {"en": "Global", "tr": "Global"},
    "region.NH":           {"en": "Northern Hemisphere", "tr": "Kuzey Yarım Küre"},
    "region.SH":           {"en": "Southern Hemisphere", "tr": "Güney Yarım Küre"},
    "unit.decade":         {"en": "°C / decade", "tr": "°C / 10 yıl"},

    # --- home ---------------------------------------------------------------------
    "home.badge":          {"en": "NASA GISTEMP v4 · PostgreSQL · 1880 – present",
                            "tr": "NASA GISTEMP v4 · PostgreSQL · 1880 – günümüz"},
    "home.sub":            {"en": "Explore 145 years of global temperature anomalies through ready-made analyses, "
                                  "or write your own SQL directly against PostgreSQL. Every chart shows the query behind it.",
                            "tr": "145 yıllık küresel sıcaklık anomalisi verisini hazır analizlerle keşfedin ya da doğrudan "
                                  "PostgreSQL üzerinde kendi SQL sorgularınızı yazın. Her grafiğin arkasındaki sorgu açık."},
    "home.globe.title":    {"en": "Warming by latitude", "tr": "Enleme göre ısınma"},
    "home.globe.caption":  {"en": "Turns slowly on its own — click or drag to take control, ▶ to let it spin again. "
                                  "Each dot shows the mean anomaly of its latitude band over the last 10 years.",
                            "tr": "Kendi kendine yavaşça döner — kontrolü almak için tıklayın ya da sürükleyin, tekrar "
                                  "döndürmek için ▶. Her nokta, bulunduğu enlem bandının son 10 yıllık ortalama "
                                  "anomalisini gösterir."},
    "home.globe.pause":    {"en": "Pause rotation", "tr": "Dönmeyi durdur"},
    "home.globe.play":     {"en": "Resume rotation", "tr": "Dönmeyi sürdür"},
    "home.fact.range":     {"en": "Coverage", "tr": "Veri aralığı"},
    "home.fact.base":      {"en": "Baseline period", "tr": "Referans dönemi"},
    "home.fact.regions":   {"en": "Regions", "tr": "Bölgeler"},
    "home.fact.regions.v": {"en": "Global · NH · SH · 8 bands", "tr": "Global · KYK · GYK · 8 bant"},
    "home.fact.version":   {"en": "Data version", "tr": "Veri sürümü"},
    "home.choose":         {"en": "Choose your path", "tr": "İki yoldan birini seçin"},
    "home.exp.sub":        {"en": "Ready-made analyses, filters and explanations",
                            "tr": "Hazır analizler, filtreler ve açıklamalar"},
    "home.exp.desc":       {"en": "Trend, hottest years, decades, hemispheres, monthly patterns, records and latitude bands. "
                                  "Every chart is powered by a SQL query you can open and modify.",
                            "tr": "Eğilim, en sıcak yıllar, on yıllar, yarım küreler, aylık desenler, rekorlar ve enlem bantları. "
                                  "Her grafik açıp değiştirebileceğiniz bir SQL sorgusundan beslenir."},
    "home.exp.cta":        {"en": "Explore the analyses", "tr": "Analizleri keşfet"},
    "home.pg.sub":         {"en": "Real PostgreSQL, safe and read-only", "tr": "Gerçek PostgreSQL, güvenli ve salt okunur"},
    "home.pg.desc":        {"en": "{count} sample queries from basic SQL to window functions, PostGIS and regression "
                                  "outputs, challenges with automatic checking, and CSV export.",
                            "tr": "Temel SQL'den window function'lara, PostGIS'e ve regresyon çıktılarına {count} örnek "
                                  "sorgu, otomatik kontrollü görevler ve CSV dışa aktarma."},
    "home.map.sub":        {"en": "25 million gridded values in PostGIS", "tr": "PostGIS'te 25 milyon ızgara değeri"},
    "home.map.desc":       {"en": "Warming rate of every country on a world map, NASA's 2°×2° grid for any year since "
                                  "1880, and up to five countries compared with the global mean.",
                            "tr": "Her ülkenin ısınma hızı dünya haritasında, 1880'den bu yana istediğin yıl için NASA'nın "
                                  "2°×2° ızgarası ve küresel ortalamayla karşılaştırılan en fazla beş ülke."},
    "home.map.cta":        {"en": "Open the map", "tr": "Haritayı aç"},
    "home.drv.sub":        {"en": "El Niño, CO₂ and the warming trend", "tr": "El Niño, CO₂ ve ısınma eğilimi"},
    "home.drv.desc":       {"en": "A regression separates El Niño from the long-term trend: the warmest years with and "
                                  "without ENSO, when warming accelerated, and why the confidence interval matters.",
                            "tr": "Bir regresyon El Niño'yu uzun dönem eğilimden ayırıyor: ENSO ile ve ENSO olmadan en "
                                  "sıcak yıllar, ısınmanın ne zaman hızlandığı ve güven aralığının neden önemli olduğu."},
    "home.drv.cta":        {"en": "See the analysis", "tr": "Analizi gör"},
    "home.pg.cta":         {"en": "Start writing SQL", "tr": "Sorgu yazmaya başla"},
    "home.findings":       {"en": "What the data says", "tr": "Veri ne söylüyor?"},

    # --- explorer -------------------------------------------------------------------
    "exp.filters":         {"en": "Filters", "tr": "Filtreler"},
    "exp.years":           {"en": "Year range", "tr": "Yıl aralığı"},
    "exp.regions":         {"en": "Regions", "tr": "Bölgeler"},
    "exp.month":           {"en": "Month", "tr": "Ay"},
    "exp.month.annual":    {"en": "Annual mean (Jan–Dec)", "tr": "Yıllık ortalama (Oca–Ara)"},
    "exp.smooth":          {"en": "5-year moving average", "tr": "5 yıllık hareketli ortalama"},
    "exp.pick_region":     {"en": "Select at least one region.", "tr": "En az bir bölge seçin."},
    "kpi.latest":          {"en": "Latest full year", "tr": "Son tam yıl"},
    "kpi.rate":            {"en": "Warming rate since 1970", "tr": "1970'ten beri ısınma hızı"},
    "kpi.hottest":         {"en": "Hottest year", "tr": "En sıcak yıl"},
    "kpi.nulls":           {"en": "Missing months (NULL)", "tr": "Eksik ay (NULL)"},
    "tab.trend":           {"en": "Global trend", "tr": "Küresel eğilim"},
    "tab.hottest":         {"en": "Hottest years", "tr": "En sıcak yıllar"},
    "tab.decades":         {"en": "Decades", "tr": "On yıllar"},
    "tab.hemis":           {"en": "Hemispheres", "tr": "Yarım küreler"},
    "tab.monthly":         {"en": "Monthly patterns", "tr": "Aylık desenler"},
    "tab.records":         {"en": "Record tracker", "tr": "Rekor takibi"},
    "tab.bands":           {"en": "Latitude bands", "tr": "Enlem bantları"},
    "trend.title":         {"en": "Temperature anomaly over time", "tr": "Zaman içinde sıcaklık anomalisi"},
    "trend.note":          {"en": "Values are departures from the 1951–1980 average, not absolute temperatures. "
                                  "The moving average smooths year-to-year swings such as El Niño to reveal the long-term trend. "
                                  "Years without all months are left out of annual means.",
                            "tr": "Değerler mutlak sıcaklık değil, 1951–1980 ortalamasından sapmadır. Hareketli ortalama, "
                                  "El Niño gibi yıllık dalgalanmaları yumuşatarak uzun dönemli eğilimi gösterir. "
                                  "Ayları eksik olan yıllar yıllık ortalamaya alınmaz."},
    "hottest.title":       {"en": "The 10 hottest years in the selected period", "tr": "Seçili dönemin en sıcak 10 yılı"},
    "hottest.note":        {"en": "Ranked with RANK(): years with the same value share a rank and the next rank is skipped.",
                            "tr": "RANK() ile sıralanır: aynı değere sahip yıllar aynı sırayı paylaşır, sonraki sıra atlanır."},
    "decades.title":       {"en": "Decade averages", "tr": "On yıllık ortalamalar"},
    "decades.note":        {"en": "Each bar averages every month of the decade. The current decade is still incomplete.",
                            "tr": "Her sütun o on yılın tüm aylarının ortalamasıdır. İçinde bulunduğumuz on yıl henüz tamamlanmadı."},
    "hemis.title":         {"en": "Northern vs Southern Hemisphere", "tr": "Kuzey ve Güney Yarım Küre"},
    "hemis.note":          {"en": "The Northern Hemisphere has more land, which warms faster than the ocean; "
                                  "the gap between the hemispheres has widened since the 1990s.",
                            "tr": "Kuzey Yarım Küre'de daha fazla kara var ve kara okyanustan hızlı ısınır; "
                                  "iki yarım küre arasındaki fark 1990'lardan beri açılıyor."},
    "monthly.title":       {"en": "Every month since the start year", "tr": "Başlangıç yılından bu yana her ay"},
    "monthly.rates":       {"en": "Warming rate by calendar month", "tr": "Takvim ayına göre ısınma hızı"},
    "monthly.note":        {"en": "Anomalies already remove the seasonal cycle, so this view does not show the hottest month "
                                  "of the year; it shows which months have departed most from their own normal.",
                            "tr": "Anomaliler mevsim etkisini zaten çıkarır; bu görünüm yılın en sıcak ayını değil, "
                                  "hangi ayların kendi normalinden en çok saptığını gösterir."},
    "records.title":       {"en": "Record-breaking years", "tr": "Rekor kıran yıllar"},
    "records.note":        {"en": "A record year is warmer than every earlier year in the selected period "
                                  "(running MAX window).",
                            "tr": "Rekor yılı, seçili dönemde kendinden önceki tüm yıllardan sıcak olan yıldır "
                                  "(kümülatif MAX penceresi)."},
    "records.legend":      {"en": "New record", "tr": "Yeni rekor"},
    "bands.title":         {"en": "Warming rate by latitude band", "tr": "Enlem bandına göre ısınma hızı"},
    "bands.note":          {"en": "Linear trend (regr_slope) over the selected years. The Arctic warms several times "
                                  "faster than the global average — Arctic amplification.",
                            "tr": "Seçili yıllardaki doğrusal eğilim (regr_slope). Arktik, küresel ortalamanın birkaç katı "
                                  "hızla ısınıyor — Arktik amplifikasyonu."},

    # --- warming map (PostGIS) ---------------------------------------------------------
    "nav.map":             {"en": "Warming Map", "tr": "Isınma Haritası"},
    "map.intro":           {"en": "Built from NASA's 2°×2° grid — about 25 million monthly values in PostGIS, "
                                  "joined with country borders.",
                            "tr": "NASA'nın 2°×2° ızgarasından üretildi: PostGIS'te yaklaşık 25 milyon aylık değer, "
                                  "ülke sınırlarıyla birleştirildi."},
    "map.tab.countries":   {"en": "Countries", "tr": "Ülkeler"},
    "map.tab.grid":        {"en": "Grid", "tr": "Izgara"},
    "map.tab.country":     {"en": "Compare countries", "tr": "Ülkeleri karşılaştır"},
    "map.compare.pick":    {"en": "Countries (up to 5)", "tr": "Ülkeler (en fazla 5)"},
    "map.compare.title":   {"en": "Countries vs the global mean", "tr": "Ülkeler ve küresel ortalama"},
    "map.compare.empty":   {"en": "Pick one or more countries to compare with the global mean.",
                            "tr": "Küresel ortalamayla karşılaştırmak için bir ya da daha fazla ülke seçin."},
    "map.compare.col.name": {"en": "Series", "tr": "Seri"},
    "map.period":          {"en": "Trend period", "tr": "Eğilim dönemi"},
    "map.countries.title": {"en": "Warming rate by country", "tr": "Ülkelere göre ısınma hızı"},
    "map.countries.note":  {"en": "Area-weighted mean of the grid cells inside each border (overlap measured with "
                                  "ST_Area on the sphere), then a linear trend. Years with less than 90% of a "
                                  "country covered by data are left out; grey = not enough data.",
                            "tr": "Her ülkenin sınırları içindeki ızgara hücrelerinin alan ağırlıklı ortalaması "
                                  "(örtüşme küre üzerinde ST_Area ile ölçülür), ardından doğrusal eğilim. Ülkenin "
                                  "%90'ından azının verisi olan yıllar alınmaz; gri = yetersiz veri."},
    "map.top":             {"en": "Fastest warming", "tr": "En hızlı ısınanlar"},
    "map.grid.title":      {"en": "Annual anomaly on the 2°×2° grid", "tr": "2°×2° ızgarada yıllık anomali"},
    "map.grid.year":       {"en": "Year", "tr": "Yıl"},
    "map.grid.note":       {"en": "Each square is one grid cell's annual mean. Empty areas had no observations "
                                  "within 1200 km — compare an early year such as 1890 with today.",
                            "tr": "Her kare bir ızgara hücresinin yıllık ortalamasıdır. Boş alanlarda 1200 km "
                                  "içinde gözlem yoktu; 1890 gibi erken bir yılı bugünle karşılaştırın."},
    "map.country.rate":    {"en": "Warming rate since 1970", "tr": "1970'ten beri ısınma hızı"},
    "map.country.recent":  {"en": "Mean of the last 10 years", "tr": "Son 10 yılın ortalaması"},
    "map.country.ratio":   {"en": "Compared with the globe", "tr": "Küresele göre"},
    "map.country.note":    {"en": "Small countries are covered by only a few cells, so their series are smoother "
                                  "versions of the surrounding region rather than local station records.",
                            "tr": "Küçük ülkeler birkaç hücreyle temsil edilir; serileri yerel istasyon kayıtları "
                                  "değil, çevre bölgenin yumuşatılmış hâlidir."},
    "map.global":          {"en": "Global mean", "tr": "Küresel ortalama"},

    # --- climate drivers (ENSO, CO2, models) ------------------------------------------------
    "nav.drivers":         {"en": "Climate Drivers", "tr": "İklim Etkenleri"},
    "drv.intro":           {"en": "Why does global temperature go up and down from year to year, and how fast is the "
                                  "underlying trend? El Niño / La Niña (ENSO), CO₂ and a regression model.",
                            "tr": "Küresel sıcaklık yıldan yıla neden iniş çıkış yapıyor ve alttaki eğilim ne kadar "
                                  "hızlı? El Niño / La Niña (ENSO), CO₂ ve bir regresyon modeli."},
    "drv.caution":         {"en": "These are statistical associations in observed data. They describe how the series "
                                  "move together; on their own they do not prove cause. Methods and limitations: "
                                  "docs/METHODS.md.",
                            "tr": "Bunlar gözlem verisindeki istatistiksel ilişkilerdir; serilerin birlikte nasıl "
                                  "hareket ettiğini gösterir, tek başlarına neden-sonuç kanıtlamaz. Yöntemler ve "
                                  "sınırlılıklar: docs/METHODS.md."},
    "drv.tab.enso":        {"en": "El Niño & La Niña", "tr": "El Niño ve La Niña"},
    "drv.tab.records":     {"en": "Records without ENSO", "tr": "ENSO'suz rekorlar"},
    "drv.tab.trend":       {"en": "Trend & breakpoint", "tr": "Eğilim ve kırılma"},
    "drv.tab.co2":         {"en": "CO₂", "tr": "CO₂"},
    "drv.enso.title":      {"en": "ENSO index and global temperature", "tr": "ENSO indeksi ve küresel sıcaklık"},
    "drv.enso.note":       {"en": "ONI ≥ +0.5 = El Niño (red), ≤ −0.5 = La Niña (blue). Warm spikes in global "
                                  "temperature tend to follow El Niño peaks by a few months.",
                            "tr": "ONI ≥ +0,5 = El Niño (kırmızı), ≤ −0,5 = La Niña (mavi). Küresel sıcaklıktaki "
                                  "sıçramalar El Niño zirvelerini birkaç ay gecikmeyle izleme eğiliminde."},
    "drv.oni":             {"en": "ONI (ENSO index)", "tr": "ONI (ENSO indeksi)"},
    "drv.phase.title":     {"en": "Departure from the trend by winter ENSO phase", "tr": "Kış ENSO durumuna göre eğilimden sapma"},
    "drv.phase.note":      {"en": "The long-term trend is removed first; otherwise El Niño years would look warm "
                                  "only because recent years are warm.",
                            "tr": "Önce uzun dönem eğilim çıkarılır; aksi hâlde El Niño yılları sadece son yıllar "
                                  "sıcak olduğu için sıcak görünürdü."},
    "drv.lag.title":       {"en": "How many months later does ENSO show up?", "tr": "ENSO kaç ay sonra etkisini gösteriyor?"},
    "drv.lag.axis":        {"en": "ONI leads temperature by (months)", "tr": "ONI'nin sıcaklıktan önceliği (ay)"},
    "drv.lag.note":        {"en": "Correlation between the detrended global anomaly and the ONI k months earlier. "
                                  "The model chooses its lag separately, with AIC.",
                            "tr": "Eğilimi çıkarılmış küresel anomali ile k ay önceki ONI arasındaki korelasyon. "
                                  "Model kendi gecikmesini ayrıca AIC ile seçer."},
    "drv.kpi.lag":         {"en": "ENSO lag (AIC)", "tr": "ENSO gecikmesi (AIC)"},
    "drv.kpi.coef":        {"en": "ENSO effect", "tr": "ENSO etkisi"},
    "drv.kpi.coef.unit":   {"en": "°C per ONI unit", "tr": "°C / ONI birimi"},
    "drv.kpi.trend":       {"en": "Trend after removing ENSO", "tr": "ENSO çıkarıldıktan sonra eğilim"},
    "drv.kpi.r2":          {"en": "Variance explained", "tr": "Açıklanan varyans"},
    "drv.months":          {"en": "months", "tr": "ay"},
    "drv.records.title":   {"en": "Observed vs ENSO-adjusted global temperature", "tr": "Gözlenen ve ENSO'dan arındırılmış küresel sıcaklık"},
    "drv.observed":        {"en": "Observed", "tr": "Gözlenen"},
    "drv.adjusted":        {"en": "ENSO removed", "tr": "ENSO çıkarılmış"},
    "drv.records.rank":    {"en": "The 10 warmest years, before and after removing ENSO", "tr": "En sıcak 10 yıl, ENSO çıkarılmadan önce ve sonra"},
    "drv.records.note":    {"en": "adjusted = observed − (ENSO coefficient × ONI three months earlier). A year that "
                                  "drops in rank owed part of its warmth to El Niño.",
                            "tr": "arındırılmış = gözlenen − (ENSO katsayısı × 3 ay önceki ONI). Sıralamada düşen bir "
                                  "yıl, sıcaklığının bir kısmını El Niño'ya borçludur."},
    "drv.trend.title":     {"en": "When did warming speed up?", "tr": "Isınma ne zaman hızlandı?"},
    "drv.trend.fit":       {"en": "Two-segment trend", "tr": "İki parçalı eğilim"},
    "drv.trend.break":     {"en": "Breakpoint {year} (approx. 95% range {low}–{high}): "
                                  "{before:+.3f} → {after:+.3f} °C / decade",
                            "tr": "Kırılma {year} (yaklaşık %95 aralığı {low}–{high}): "
                                  "{before:+.3f} → {after:+.3f} °C / 10 yıl"},
    "drv.profile.title":   {"en": "Fit error for every candidate breakpoint", "tr": "Her aday kırılma yılı için uyum hatası"},
    "drv.profile.axis":    {"en": "Residual sum of squares", "tr": "Artık kareler toplamı"},
    "drv.ci.title":        {"en": "Why the confidence interval matters", "tr": "Güven aralığı neden önemli?"},
    "drv.ci.note":         {"en": "Consecutive months are not independent (residual autocorrelation {ac:.2f}). The "
                                  "classical interval ignores that and is too narrow; Newey-West corrects it.",
                            "tr": "Ardışık aylar birbirinden bağımsız değil (artık otokorelasyonu {ac:.2f}). Klasik "
                                  "aralık bunu yok sayar ve fazla dardır; Newey-West bunu düzeltir."},
    "drv.ci.col.series":   {"en": "Series", "tr": "Seri"},
    "drv.ci.col.method":   {"en": "Interval", "tr": "Aralık"},
    "drv.ci.col.trend":    {"en": "Trend (°C / decade)", "tr": "Eğilim (°C / 10 yıl)"},
    "drv.ci.col.ci":       {"en": "95% interval", "tr": "%95 aralık"},
    "drv.ci.col.width":    {"en": "± width", "tr": "± genişlik"},
    "drv.ci.monthly":      {"en": "Monthly, with ENSO", "tr": "Aylık, ENSO ile"},
    "drv.ci.annual":       {"en": "Annual means", "tr": "Yıllık ortalamalar"},
    "drv.ci.classical":    {"en": "Classical", "tr": "Klasik"},
    "drv.co2.title":       {"en": "The Keeling curve: CO₂ at Mauna Loa", "tr": "Keeling eğrisi: Mauna Loa'da CO₂"},
    "drv.co2.monthly":     {"en": "Monthly mean", "tr": "Aylık ortalama"},
    "drv.co2.trend":       {"en": "Seasonally adjusted", "tr": "Mevsimsellikten arındırılmış"},
    "drv.scatter.title":   {"en": "Annual global temperature against CO₂", "tr": "Yıllık küresel sıcaklık ve CO₂"},
    "drv.scatter.note":    {"en": "{slope:.2f} °C per 100 ppm, R² = {r2:.2f} ({first}–{last}). Two rising series "
                                  "correlate; the physics of greenhouse gases, not this line, is the evidence of cause.",
                            "tr": "100 ppm başına {slope:.2f} °C, R² = {r2:.2f} ({first}–{last}). Birlikte yükselen iki "
                                  "seri ilişkili çıkar; nedenin kanıtı bu doğru değil, sera gazlarının fiziğidir."},

    # --- playground ---------------------------------------------------------------
    "pg.schema":           {"en": "Schema · playground", "tr": "Şema · playground"},
    "pg.samples":          {"en": "Sample queries", "tr": "Örnek sorgular"},
    "pg.level":            {"en": "Level", "tr": "Seviye"},
    "pg.level.basic":      {"en": "Basic", "tr": "Temel"},
    "pg.level.intermediate": {"en": "Intermediate", "tr": "Orta"},
    "pg.level.advanced":   {"en": "Advanced", "tr": "İleri"},
    "pg.level.spatial":    {"en": "Spatial", "tr": "Mekânsal"},
    "pg.level.drivers":    {"en": "Drivers", "tr": "Etkenler"},
    "pg.schema.series":    {"en": "Temperature series", "tr": "Sıcaklık serileri"},
    "pg.schema.spatial":   {"en": "Grid and countries (PostGIS)", "tr": "Izgara ve ülkeler (PostGIS)"},
    "pg.schema.drivers":   {"en": "ENSO, CO₂ and model results", "tr": "ENSO, CO₂ ve model sonuçları"},
    "pg.samples.pick":     {"en": "Load a sample query", "tr": "Örnek sorgu yükle"},
    "pg.editor":           {"en": "SQL query", "tr": "SQL sorgusu"},
    "pg.placeholder":      {"en": "Write your SQL here, or load a sample query from the left…\n\n"
                                  "Start with v_monthly (region, year, month, anomaly). Every table is listed under Schema.",
                            "tr": "SQL sorgunuzu buraya yazın ya da soldan bir örnek sorgu yükleyin…\n\n"
                                  "v_monthly ile başlayın (region, year, month, anomaly). Tüm tablolar Şema altında."},
    "pg.badges":           {"en": "🔒 Read-only · 🧮 cost checked before running · ⏱ 3 s timeout · max {rows:,} rows",
                            "tr": "🔒 Salt okunur · 🧮 çalıştırmadan önce maliyet kontrolü · ⏱ 3 sn zaman aşımı · "
                                  "en fazla {rows:,} satır"},
    "pg.run":              {"en": "Run query", "tr": "Çalıştır"},
    "pg.ok":               {"en": "{rows:,} rows · {ms:,.0f} ms · estimated cost {cost:,.0f}",
                            "tr": "{rows:,} satır · {ms:,.0f} ms · tahmini maliyet {cost:,.0f}"},
    "pg.cost.blocked":     {"en": "This query looks too expensive to run",
                            "tr": "Bu sorgu çalıştırmak için fazla maliyetli görünüyor"},
    "pg.cost.detail":      {"en": "PostgreSQL's planner estimates a cost of {cost:,.0f} (limit {limit:,.0f}); the "
                                  "most expensive step is a {node}. Nothing was executed. Usually a join is missing "
                                  "its ON condition, or a query scans the 25-million-row v_grid where v_grid_annual "
                                  "or a WHERE on obs_date would do.",
                            "tr": "PostgreSQL'in planlayıcısı {cost:,.0f} maliyet tahmin ediyor (sınır {limit:,.0f}); "
                                  "en pahalı adım: {node}. Hiçbir şey çalıştırılmadı. Genellikle bir JOIN'in ON koşulu "
                                  "eksiktir ya da v_grid_annual veya obs_date üzerinde bir WHERE yeterliyken 25 milyon "
                                  "satırlık v_grid taranıyordur."},
    "pg.truncated":        {"en": "Showing the first {rows:,} rows only.", "tr": "Yalnızca ilk {rows:,} satır gösteriliyor."},
    "pg.empty_result":     {"en": "The query ran but returned no rows.", "tr": "Sorgu çalıştı ama satır döndürmedi."},
    "pg.blocked":          {"en": "This query was not run", "tr": "Bu sorgu çalıştırılmadı"},
    "pg.chart":            {"en": "Turn into chart", "tr": "Grafiğe dönüştür"},
    "pg.chart.x":          {"en": "X axis", "tr": "X ekseni"},
    "pg.chart.y":          {"en": "Y axis", "tr": "Y ekseni"},
    "pg.challenges":       {"en": "Challenges", "tr": "Görevler"},
    "pg.ch.check":         {"en": "Check my result", "tr": "Sonucumu kontrol et"},
    "pg.ch.hint":          {"en": "Hint", "tr": "İpucu"},
    "pg.ch.correct":       {"en": "Correct! ✓", "tr": "Doğru! ✓"},
    "pg.ch.wrong":         {"en": "Not yet — {detail}", "tr": "Henüz değil — {detail}"},
    "pg.ch.run_first":     {"en": "Run your query first.", "tr": "Önce sorgunuzu çalıştırın."},
    "pg.ch.cols":          {"en": "expected {expected} columns, got {got}.", "tr": "{expected} sütun bekleniyordu, {got} geldi."},
    "pg.ch.rows":          {"en": "expected {expected} rows, got {got}.", "tr": "{expected} satır bekleniyordu, {got} geldi."},
    "pg.ch.values":        {"en": "the row count matches but some values differ.", "tr": "satır sayısı doğru ama bazı değerler farklı."},
    "pg.ch.progress":      {"en": "{done} / {total} solved", "tr": "{done} / {total} çözüldü"},

    # --- friendly database errors ---------------------------------------------------
    "err.timeout":         {"en": "The query took longer than 3 seconds and was stopped. Try adding filters or a LIMIT.",
                            "tr": "Sorgu 3 saniyeden uzun sürdü ve durduruldu. Filtre ya da LIMIT eklemeyi deneyin."},
    "err.permission":      {"en": "Permission denied: the Playground can only read the views listed under Schema.",
                            "tr": "Yetki yok: Playground yalnızca Şema altında listelenen view'ları okuyabilir."},
    "err.readonly":        {"en": "The Playground is read-only.", "tr": "Playground salt okunurdur."},
    "err.undefined_table": {"en": "Unknown table or view. Available: v_monthly, v_annual, regions, datasets.",
                            "tr": "Bilinmeyen tablo ya da view. Kullanılabilenler: v_monthly, v_annual, regions, datasets."},
    "err.undefined_column":{"en": "Unknown column. Check the column names under Schema.",
                            "tr": "Bilinmeyen sütun. Sütun adlarını Şema altında kontrol edin."},
    "err.syntax":          {"en": "SQL syntax error.", "tr": "SQL söz dizimi hatası."},
    "err.group_by":        {"en": "Every selected column must be in GROUP BY or inside an aggregate such as AVG().",
                            "tr": "Seçilen her sütun GROUP BY içinde ya da AVG() gibi bir toplama fonksiyonunun içinde olmalı."},
    "err.other":           {"en": "The database returned an error.", "tr": "Veritabanı bir hata döndürdü."},
}

MONTH_NAMES = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "tr": ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
}


def lang() -> str:
    return st.session_state.get("lang", "en")


def t(key: str, **values) -> str:
    entry = TEXT.get(key)
    if entry is None:
        return key
    text = entry.get(lang()) or entry["en"]
    return text.format(**values) if values else text


def month_names() -> list[str]:
    return MONTH_NAMES[lang()]


def language_toggle() -> None:
    """EN / TR switch, pinned into the top bar of every page by CSS (components.page_style)."""
    current = "TR" if lang() == "tr" else "EN"
    choice = st.segmented_control(
        t("lang.label"), list(LANGUAGES), default=current, key="lang_toggle",
        label_visibility="collapsed",
    )
    if choice and LANGUAGES[choice] != lang():
        st.session_state["lang"] = LANGUAGES[choice]
        st.rerun()
