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
    "home.globe.caption":  {"en": "Drag to rotate · each dot shows the mean anomaly of its latitude band over the last 10 years",
                            "tr": "Döndürmek için sürükleyin · her nokta, bulunduğu enlem bandının son 10 yıllık ortalama anomalisini gösterir"},
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
    "home.pg.desc":        {"en": "37 sample queries from basic to advanced, challenges with automatic checking, "
                                  "and CSV export.",
                            "tr": "Temelden ileriye 37 örnek sorgu, otomatik kontrollü görevler ve CSV dışa aktarma."},
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

    # --- playground ---------------------------------------------------------------
    "pg.schema":           {"en": "Schema · playground", "tr": "Şema · playground"},
    "pg.samples":          {"en": "Sample queries", "tr": "Örnek sorgular"},
    "pg.samples.pick":     {"en": "Load a sample query", "tr": "Örnek sorgu yükle"},
    "pg.editor":           {"en": "SQL query", "tr": "SQL sorgusu"},
    "pg.placeholder":      {"en": "Write your SQL here, or load a sample query from the left…\n\n"
                                  "Tables: v_monthly, v_annual, regions, datasets",
                            "tr": "SQL sorgunuzu buraya yazın ya da soldan bir örnek sorgu yükleyin…\n\n"
                                  "Tablolar: v_monthly, v_annual, regions, datasets"},
    "pg.badges":           {"en": "🔒 Read-only · ⏱ 3 s timeout · max {rows:,} rows",
                            "tr": "🔒 Salt okunur · ⏱ 3 sn zaman aşımı · en fazla {rows:,} satır"},
    "pg.run":              {"en": "Run query", "tr": "Çalıştır"},
    "pg.ok":               {"en": "{rows:,} rows · {ms:,.0f} ms", "tr": "{rows:,} satır · {ms:,.0f} ms"},
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
    """EN / TR switch shown at the top right of every page."""
    current = "TR" if lang() == "tr" else "EN"
    _, slot = st.columns([10, 1.4])
    choice = slot.segmented_control(
        t("lang.label"), list(LANGUAGES), default=current, key="lang_toggle",
        label_visibility="collapsed",
    )
    if choice and LANGUAGES[choice] != lang():
        st.session_state["lang"] = LANGUAGES[choice]
        st.rerun()
