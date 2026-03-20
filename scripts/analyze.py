#!/usr/bin/env python3
"""
PICF 2025-2026 — Seniorní datová analýza
Multikanálový audit: Facebook, Instagram, YouTube
"""

import pandas as pd
import json
import os
import re
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
CLEAN = os.path.join(BASE, "data", "clean")
os.makedirs(CLEAN, exist_ok=True)

# ── Pomocné funkce ──────────────────────────────────────────────

def try_read_csv(path, **kwargs):
    """Načte CSV s fallbackem na cp1250."""
    for enc in ["utf-8-sig", "utf-8", "cp1250", "latin1"]:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError(f"Nepodařilo se načíst {path}")


def to_numeric_safe(series):
    """Převede sloupec na číslo, NaN pro nečíselné."""
    return pd.to_numeric(series.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def detect_indian_mentions(text):
    """Detekuje zmínky o indických hráčích v textu."""
    if not isinstance(text, str):
        return []
    players = {
        "Gukesh": ["gukesh", "dommaraju"],
        "Praggnanandhaa": ["praggnanandhaa", "pragg"],
        "Vidit": ["vidit", "gujrathi"],
        "Arjun Erigaisi": ["erigaisi", "arjun"],
        "Sasikiran": ["sasikiran", "krishnan"],
    }
    found = []
    lower = text.lower()
    for name, keywords in players.items():
        if any(kw in lower for kw in keywords):
            found.append(name)
    return found


# ── 1. FACEBOOK ──────────────────────────────────────────────────

print("=" * 60)
print("📘 FACEBOOK ANALÝZA")
print("=" * 60)

fb25 = try_read_csv(os.path.join(RAW, "facebook_2025.csv"))
fb26 = try_read_csv(os.path.join(RAW, "facebook_2026.csv"))

# Sjednotit sloupce
fb25["Rok"] = 2025
fb26["Rok"] = 2026

# Převod datumů
for df in [fb25, fb26]:
    # "Datum" je "Dlouhodobě", skutečné datum je v "Čas zveřejnění"
    df["Datum"] = pd.to_datetime(df["Čas zveřejnění"], errors="coerce")
    for col in ["Zhlédnutí", "Dosah", "Reakce, komentáře a sdílení", "Reakce", "Komentáře", "Sdílení", "Celkem kliknutí"]:
        if col in df.columns:
            df[col] = to_numeric_safe(df[col])

# Klíčové metriky FB
fb_stats = {}
for year, df in [(2025, fb25), (2026, fb26)]:
    fb_stats[year] = {
        "pocet_prispevku": len(df),
        "celkovy_dosah": int(df["Dosah"].sum()) if "Dosah" in df.columns else 0,
        "celkove_zhlednuti": int(df["Zhlédnutí"].sum()) if "Zhlédnutí" in df.columns else 0,
        "celkove_reakce": int(df["Reakce"].sum()) if "Reakce" in df.columns else 0,
        "celkove_komentare": int(df["Komentáře"].sum()) if "Komentáře" in df.columns else 0,
        "celkove_sdileni": int(df["Sdílení"].sum()) if "Sdílení" in df.columns else 0,
        "celkove_kliknuti": int(df["Celkem kliknutí"].sum()) if "Celkem kliknutí" in df.columns else 0,
        "celkovy_engagement": int(df["Reakce, komentáře a sdílení"].sum()) if "Reakce, komentáře a sdílení" in df.columns else 0,
    }
    print(f"\n📊 Facebook {year}:")
    for k, v in fb_stats[year].items():
        print(f"   {k}: {v:,}")

# Engagement per post
for year in [2025, 2026]:
    s = fb_stats[year]
    if s["pocet_prispevku"] > 0:
        s["engagement_per_post"] = round(s["celkovy_engagement"] / s["pocet_prispevku"], 1)
        s["dosah_per_post"] = round(s["celkovy_dosah"] / s["pocet_prispevku"], 1)

# YoY
print("\n📈 Facebook YoY růst:")
for metric in ["pocet_prispevku", "celkovy_dosah", "celkovy_engagement", "celkove_zhlednuti"]:
    v25 = fb_stats[2025][metric]
    v26 = fb_stats[2026][metric]
    if v25 > 0:
        growth = ((v26 - v25) / v25) * 100
        print(f"   {metric}: {v25:,} → {v26:,} ({growth:+.1f}%)")

# Indian Factor - FB
print("\n🇮🇳 Indian Factor (Facebook 2026):")
fb26["indian_players"] = fb26["Název"].apply(detect_indian_mentions)
fb26["has_indian"] = fb26["indian_players"].apply(lambda x: len(x) > 0)
indian_fb = fb26[fb26["has_indian"]]
non_indian_fb = fb26[~fb26["has_indian"]]

if len(indian_fb) > 0 and len(non_indian_fb) > 0:
    avg_reach_indian = indian_fb["Dosah"].mean()
    avg_reach_other = non_indian_fb["Dosah"].mean()
    print(f"   Příspěvky s indickými hráči: {len(indian_fb)}")
    print(f"   Průměrný dosah (s indickými): {avg_reach_indian:,.0f}")
    print(f"   Průměrný dosah (ostatní): {avg_reach_other:,.0f}")
    if avg_reach_other > 0:
        print(f"   Multiplikátor: {avg_reach_indian/avg_reach_other:.1f}x")

# Top FB příspěvky 2026
print("\n🏆 Top 5 Facebook příspěvky 2026 (dle dosahu):")
top_fb = fb26.nlargest(5, "Dosah")[["Název", "Dosah", "Reakce, komentáře a sdílení", "Datum"]].copy()
top_fb["Název"] = top_fb["Název"].str[:80]
for _, row in top_fb.iterrows():
    print(f"   📌 Dosah: {row['Dosah']:,.0f} | Eng: {row['Reakce, komentáře a sdílení']:,.0f} | {row['Název']}...")


# ── 2. INSTAGRAM ──────────────────────────────────────────────────

print("\n" + "=" * 60)
print("📸 INSTAGRAM ANALÝZA")
print("=" * 60)

ig25 = try_read_csv(os.path.join(RAW, "instagram_2025.csv"))
ig26 = try_read_csv(os.path.join(RAW, "instagram_2026.csv"))

ig25["Rok"] = 2025
ig26["Rok"] = 2026

for df in [ig25, ig26]:
    df["Datum"] = pd.to_datetime(df["Čas zveřejnění"], errors="coerce")
    for col in ["Zobrazení", "Dosah", "To se mi líbí", "Sdílené", "Komentáře", "Uložení"]:
        if col in df.columns:
            df[col] = to_numeric_safe(df[col])

ig_stats = {}
for year, df in [(2025, ig25), (2026, ig26)]:
    ig_stats[year] = {
        "pocet_prispevku": len(df),
        "celkovy_dosah": int(df["Dosah"].sum()) if "Dosah" in df.columns else 0,
        "celkove_zobrazeni": int(df["Zobrazení"].sum()) if "Zobrazení" in df.columns else 0,
        "celkove_lajky": int(df["To se mi líbí"].sum()) if "To se mi líbí" in df.columns else 0,
        "celkove_komentare": int(df["Komentáře"].sum()) if "Komentáře" in df.columns else 0,
        "celkove_sdileni": int(df["Sdílené"].sum()) if "Sdílené" in df.columns else 0,
        "celkove_ulozeni": int(df["Uložení"].sum()) if "Uložení" in df.columns else 0,
    }
    ig_stats[year]["celkovy_engagement"] = (
        ig_stats[year]["celkove_lajky"] + ig_stats[year]["celkove_komentare"] +
        ig_stats[year]["celkove_sdileni"] + ig_stats[year]["celkove_ulozeni"]
    )
    print(f"\n📊 Instagram {year}:")
    for k, v in ig_stats[year].items():
        print(f"   {k}: {v:,}")

# Engagement per post
for year in [2025, 2026]:
    s = ig_stats[year]
    if s["pocet_prispevku"] > 0:
        s["engagement_per_post"] = round(s["celkovy_engagement"] / s["pocet_prispevku"], 1)
        s["dosah_per_post"] = round(s["celkovy_dosah"] / s["pocet_prispevku"], 1)

print("\n📈 Instagram YoY růst:")
for metric in ["pocet_prispevku", "celkovy_dosah", "celkovy_engagement", "celkove_zobrazeni"]:
    v25 = ig_stats[2025][metric]
    v26 = ig_stats[2026][metric]
    if v25 > 0:
        growth = ((v26 - v25) / v25) * 100
        print(f"   {metric}: {v25:,} → {v26:,} ({growth:+.1f}%)")

# Indian Factor - IG
print("\n🇮🇳 Indian Factor (Instagram 2026):")
ig26["indian_players"] = ig26["Popis"].apply(detect_indian_mentions)
ig26["has_indian"] = ig26["indian_players"].apply(lambda x: len(x) > 0)
indian_ig = ig26[ig26["has_indian"]]
non_indian_ig = ig26[~ig26["has_indian"]]

if len(indian_ig) > 0 and len(non_indian_ig) > 0:
    avg_reach_indian_ig = indian_ig["Dosah"].mean()
    avg_reach_other_ig = non_indian_ig["Dosah"].mean()
    print(f"   Příspěvky s indickými hráči: {len(indian_ig)}")
    print(f"   Průměrný dosah (s indickými): {avg_reach_indian_ig:,.0f}")
    print(f"   Průměrný dosah (ostatní): {avg_reach_other_ig:,.0f}")
    if avg_reach_other_ig > 0:
        print(f"   Multiplikátor: {avg_reach_indian_ig/avg_reach_other_ig:.1f}x")

# Top IG příspěvky 2026
print("\n🏆 Top 5 Instagram příspěvky 2026 (dle dosahu):")
top_ig = ig26.nlargest(5, "Dosah")[["Popis", "Dosah", "To se mi líbí", "Sdílené", "Datum"]].copy()
top_ig["Popis"] = top_ig["Popis"].str[:80]
for _, row in top_ig.iterrows():
    likes = row.get("To se mi líbí", 0)
    shares = row.get("Sdílené", 0)
    print(f"   📌 Dosah: {row['Dosah']:,.0f} | ❤️ {likes:,.0f} | 🔁 {shares:,.0f} | {row['Popis']}...")


# ── 3. YOUTUBE ──────────────────────────────────────────────────

print("\n" + "=" * 60)
print("📺 YOUTUBE ANALÝZA")
print("=" * 60)

yt_tab25 = try_read_csv(os.path.join(RAW, "Data v tabulce.csv"))
yt_tab26 = try_read_csv(os.path.join(RAW, "Data v tabulce (srovnání).csv"))
yt_sum25 = try_read_csv(os.path.join(RAW, "Součty.csv"))
yt_sum26 = try_read_csv(os.path.join(RAW, "Součty (srovnání).csv"))
yt_graf25 = try_read_csv(os.path.join(RAW, "Data v grafu.csv"))
yt_graf26 = try_read_csv(os.path.join(RAW, "Data v grafu (srovnání).csv"))

# Celkové součty z tabulky (první řádek = Celkem)
yt_stats = {}
for year, df in [(2025, yt_tab25), (2026, yt_tab26)]:
    total_row = df[df["Obsah"] == "Celkem"].iloc[0] if len(df[df["Obsah"] == "Celkem"]) > 0 else df.iloc[0]
    yt_stats[year] = {
        "pocet_videi": len(df) - 1,  # minus total row
        "celkove_zhlednuti": int(to_numeric_safe(pd.Series([total_row.get("Zhlédnutí", 0)])).iloc[0]),
        "doba_sledovani_hodin": float(str(total_row.get("Doba sledování (hodin)", 0)).replace(",", "")),
        "odberatele": int(to_numeric_safe(pd.Series([total_row.get("Odběratelé", 0)])).iloc[0]),
        "zobrazeni": int(to_numeric_safe(pd.Series([total_row.get("Zobrazení", 0)])).iloc[0]),
    }
    print(f"\n📊 YouTube {year}:")
    for k, v in yt_stats[year].items():
        print(f"   {k}: {v:,}")

print("\n📈 YouTube YoY růst:")
for metric in ["celkove_zhlednuti", "doba_sledovani_hodin", "odberatele", "zobrazeni"]:
    v25 = yt_stats[2025][metric]
    v26 = yt_stats[2026][metric]
    if v25 > 0:
        growth = ((v26 - v25) / v25) * 100
        print(f"   {metric}: {v25:,} → {v26:,} ({growth:+.1f}%)")

# Top YT videa 2026
print("\n🏆 Top 5 YouTube videa 2026 (dle zhlédnutí):")
yt_vids26 = yt_tab26[yt_tab26["Obsah"] != "Celkem"].copy()
yt_vids26["Zhlédnutí"] = to_numeric_safe(yt_vids26["Zhlédnutí"])
top_yt = yt_vids26.nlargest(5, "Zhlédnutí")[["Název videa", "Zhlédnutí", "Doba sledování (hodin)", "Odběratelé"]]
for _, row in top_yt.iterrows():
    print(f"   📌 {row['Zhlédnutí']:,.0f} zhlédnutí | {row['Název videa'][:70]}")

# Indian Factor - YT
print("\n🇮🇳 Indian Factor (YouTube 2026):")
yt_vids26["indian_players"] = yt_vids26["Název videa"].apply(detect_indian_mentions)
yt_vids26["has_indian"] = yt_vids26["indian_players"].apply(lambda x: len(x) > 0)
indian_yt = yt_vids26[yt_vids26["has_indian"]]
non_indian_yt = yt_vids26[~yt_vids26["has_indian"]]

if len(indian_yt) > 0 and len(non_indian_yt) > 0:
    avg_views_indian = indian_yt["Zhlédnutí"].mean()
    avg_views_other = non_indian_yt["Zhlédnutí"].mean()
    print(f"   Videa s indickými hráči: {len(indian_yt)}")
    print(f"   Průměrná zhlédnutí (s indickými): {avg_views_indian:,.0f}")
    print(f"   Průměrná zhlédnutí (ostatní): {avg_views_other:,.0f}")
    if avg_views_other > 0:
        print(f"   Multiplikátor: {avg_views_indian/avg_views_other:.1f}x")


# ── 4. DENNÍ ČASOVÉ ŘADY pro grafy ──────────────────────────────

print("\n" + "=" * 60)
print("📅 DENNÍ ČASOVÉ ŘADY")
print("=" * 60)

# Facebook denní agregace
fb26_daily = fb26.dropna(subset=["Datum"]).groupby(fb26["Datum"].dt.date).agg(
    dosah=("Dosah", "sum"),
    engagement=("Reakce, komentáře a sdílení", "sum"),
    prispevky=("Dosah", "count")
).reset_index()
fb26_daily.columns = ["datum", "dosah", "engagement", "prispevky"]

fb25_daily = fb25.dropna(subset=["Datum"]).groupby(fb25["Datum"].dt.date).agg(
    dosah=("Dosah", "sum"),
    engagement=("Reakce, komentáře a sdílení", "sum"),
    prispevky=("Dosah", "count")
).reset_index()
fb25_daily.columns = ["datum", "dosah", "engagement", "prispevky"]

# Instagram denní agregace
ig26_daily = ig26.dropna(subset=["Datum"]).groupby(ig26["Datum"].dt.date).agg(
    dosah=("Dosah", "sum"),
    zobrazeni=("Zobrazení", "sum"),
    engagement=("To se mi líbí", "sum"),
    prispevky=("Dosah", "count")
).reset_index()
ig26_daily.columns = ["datum", "dosah", "zobrazeni", "engagement", "prispevky"]

ig25_daily = ig25.dropna(subset=["Datum"]).groupby(ig25["Datum"].dt.date).agg(
    dosah=("Dosah", "sum"),
    zobrazeni=("Zobrazení", "sum"),
    engagement=("To se mi líbí", "sum"),
    prispevky=("Dosah", "count")
).reset_index()
ig25_daily.columns = ["datum", "dosah", "zobrazeni", "engagement", "prispevky"]

# YouTube denní (ze součtů)
yt_daily25 = yt_sum25.copy()
yt_daily25.columns = ["datum", "zhlednuti"]
yt_daily25["datum"] = pd.to_datetime(yt_daily25["datum"]).dt.date

yt_daily26 = yt_sum26.copy()
yt_daily26.columns = ["datum", "zhlednuti"]
yt_daily26["datum"] = pd.to_datetime(yt_daily26["datum"]).dt.date

print(f"   FB 2025 denní řádků: {len(fb25_daily)}")
print(f"   FB 2026 denní řádků: {len(fb26_daily)}")
print(f"   IG 2025 denní řádků: {len(ig25_daily)}")
print(f"   IG 2026 denní řádků: {len(ig26_daily)}")
print(f"   YT 2025 denní řádků: {len(yt_daily25)}")
print(f"   YT 2026 denní řádků: {len(yt_daily26)}")


# ── 5. CROSS-PLATFORM EFFICIENCY ────────────────────────────────

print("\n" + "=" * 60)
print("⚡ ENGAGEMENT EFFICIENCY")
print("=" * 60)

efficiency = {}
for platform, stats_25, stats_26 in [
    ("Facebook", fb_stats[2025], fb_stats[2026]),
    ("Instagram", ig_stats[2025], ig_stats[2026]),
]:
    for year, stats in [(2025, stats_25), (2026, stats_26)]:
        n = stats["pocet_prispevku"]
        eng = stats["celkovy_engagement"]
        reach = stats["celkovy_dosah"]
        efficiency[f"{platform}_{year}"] = {
            "platforma": platform,
            "rok": year,
            "prispevky": n,
            "engagement_total": eng,
            "dosah_total": reach,
            "engagement_per_post": round(eng / n, 1) if n > 0 else 0,
            "dosah_per_post": round(reach / n, 1) if n > 0 else 0,
        }
        print(f"   {platform} {year}: {n} příspěvků → {eng:,} eng ({round(eng/n,1) if n>0 else 0}/post) | {reach:,} dosah ({round(reach/n,1) if n>0 else 0}/post)")

# YouTube efficiency
for year, stats in [(2025, yt_stats[2025]), (2026, yt_stats[2026])]:
    n = stats["pocet_videi"]
    views = stats["celkove_zhlednuti"]
    efficiency[f"YouTube_{year}"] = {
        "platforma": "YouTube",
        "rok": year,
        "prispevky": n,
        "zhlednuti_total": views,
        "zhlednuti_per_video": round(views / n, 1) if n > 0 else 0,
    }
    print(f"   YouTube {year}: {n} videí → {views:,} zhlédnutí ({round(views/n,1) if n>0 else 0}/video)")


# ── 6. TOP 3 MOMENTY (cross-platform) ───────────────────────────

print("\n" + "=" * 60)
print("🌟 TOP 3 MOMENTY FESTIVALU 2026")
print("=" * 60)

# Sbírka top příspěvků
moments = []

# Top FB
if len(fb26) > 0:
    for _, row in fb26.nlargest(3, "Dosah").iterrows():
        moments.append({
            "platforma": "Facebook",
            "nazev": str(row.get("Název", ""))[:120],
            "dosah": int(row.get("Dosah", 0)),
            "engagement": int(row.get("Reakce, komentáře a sdílení", 0)),
            "datum": str(row.get("Datum", ""))[:10],
            "link": str(row.get("Přímý odkaz", "")),
            "indian": detect_indian_mentions(str(row.get("Název", ""))),
        })

# Top IG
if len(ig26) > 0:
    for _, row in ig26.nlargest(3, "Dosah").iterrows():
        moments.append({
            "platforma": "Instagram",
            "nazev": str(row.get("Popis", ""))[:120],
            "dosah": int(row.get("Dosah", 0)),
            "engagement": int(row.get("To se mi líbí", 0)) + int(row.get("Sdílené", 0)),
            "datum": str(row.get("Datum", ""))[:10],
            "link": str(row.get("Přímý odkaz", "")),
            "indian": detect_indian_mentions(str(row.get("Popis", ""))),
        })

# Top YT
if len(yt_vids26) > 0:
    for _, row in yt_vids26.nlargest(3, "Zhlédnutí").iterrows():
        moments.append({
            "platforma": "YouTube",
            "nazev": str(row.get("Název videa", ""))[:120],
            "dosah": int(row.get("Zhlédnutí", 0)),
            "engagement": int(row.get("Odběratelé", 0)),
            "datum": str(row.get("Čas zveřejnění videa", "")),
            "indian": detect_indian_mentions(str(row.get("Název videa", ""))),
        })

# Seřadit dle dosahu a vzít top 3
moments.sort(key=lambda x: x["dosah"], reverse=True)
top3 = moments[:3]
for i, m in enumerate(top3, 1):
    indian_str = f" 🇮🇳 {', '.join(m['indian'])}" if m['indian'] else ""
    print(f"   #{i} [{m['platforma']}] Dosah: {m['dosah']:,} | {m['nazev'][:70]}...{indian_str}")


# ── 7. EXPORT pro HTML dashboard ────────────────────────────────

print("\n" + "=" * 60)
print("💾 EXPORT DAT PRO DASHBOARD")
print("=" * 60)

dashboard_data = {
    "generated_at": datetime.now().isoformat(),
    "facebook": {
        "stats_2025": fb_stats[2025],
        "stats_2026": fb_stats[2026],
        "daily_2025": [{"datum": str(r["datum"]), "dosah": int(r["dosah"]), "engagement": int(r["engagement"])} for _, r in fb25_daily.iterrows()],
        "daily_2026": [{"datum": str(r["datum"]), "dosah": int(r["dosah"]), "engagement": int(r["engagement"])} for _, r in fb26_daily.iterrows()],
        "indian_factor_2026": {
            "posts_with_indian": int(len(indian_fb)),
            "posts_without": int(len(non_indian_fb)),
            "avg_reach_indian": float(indian_fb["Dosah"].mean()) if len(indian_fb) > 0 else 0,
            "avg_reach_other": float(non_indian_fb["Dosah"].mean()) if len(non_indian_fb) > 0 else 0,
        },
    },
    "instagram": {
        "stats_2025": ig_stats[2025],
        "stats_2026": ig_stats[2026],
        "daily_2025": [{"datum": str(r["datum"]), "dosah": int(r["dosah"]), "zobrazeni": int(r["zobrazeni"]), "engagement": int(r["engagement"])} for _, r in ig25_daily.iterrows()],
        "daily_2026": [{"datum": str(r["datum"]), "dosah": int(r["dosah"]), "zobrazeni": int(r["zobrazeni"]), "engagement": int(r["engagement"])} for _, r in ig26_daily.iterrows()],
        "indian_factor_2026": {
            "posts_with_indian": int(len(indian_ig)),
            "posts_without": int(len(non_indian_ig)),
            "avg_reach_indian": float(indian_ig["Dosah"].mean()) if len(indian_ig) > 0 else 0,
            "avg_reach_other": float(non_indian_ig["Dosah"].mean()) if len(non_indian_ig) > 0 else 0,
        },
    },
    "youtube": {
        "stats_2025": yt_stats[2025],
        "stats_2026": yt_stats[2026],
        "daily_2025": [{"datum": str(r["datum"]), "zhlednuti": int(r["zhlednuti"])} for _, r in yt_daily25.iterrows()],
        "daily_2026": [{"datum": str(r["datum"]), "zhlednuti": int(r["zhlednuti"])} for _, r in yt_daily26.iterrows()],
        "indian_factor_2026": {
            "videos_with_indian": int(len(indian_yt)),
            "videos_without": int(len(non_indian_yt)),
            "avg_views_indian": float(indian_yt["Zhlédnutí"].mean()) if len(indian_yt) > 0 else 0,
            "avg_views_other": float(non_indian_yt["Zhlédnutí"].mean()) if len(non_indian_yt) > 0 else 0,
        },
    },
    "efficiency": efficiency,
    "top3_moments": top3,
}

output_path = os.path.join(CLEAN, "dashboard_data.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(dashboard_data, f, ensure_ascii=False, indent=2, default=str)

print(f"   ✅ Dashboard data exportována: {output_path}")
print(f"   Velikost: {os.path.getsize(output_path):,} bytes")
print("\n🎯 ANALÝZA DOKONČENA")
