#!/usr/bin/env python3
"""Build QA speech samples for test-video-asset (49 languages).

Sources (in order):
  1. Existing en/fr/es (skip unless --force)
  2. Curated archive.org LibriVox identifiers
  3. Auto-discovery: archive.org advancedsearch librivox language:{iso639_2}
  4. Fallback: Google FLEURS (CC BY 4.0) for sparse LibriVox languages

Output per language:
  audio/{code}/qa-{code}-001.aac
  audio/{code}/qa-{code}-001.txt (when transcript available)
  audio/manifest.json
  audio/ATTRIBUTION.md
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "audio"
CLIP_SEC = 35
OFFSET_SEC = 20

LANGS = [
    ("ar", "ara", "Arabic"),
    ("bg", "bul", "Bulgarian"),
    ("bn", "ben", "Bengali"),
    ("ca", "cat", "Catalan"),
    ("cs", "ces", "Czech"),
    ("da", "dan", "Danish"),
    ("de", "deu", "German"),
    ("el", "ell", "Greek"),
    ("en", "eng", "English"),
    ("es", "spa", "Spanish"),
    ("et", "est", "Estonian"),
    ("eu", "eus", "Basque"),
    ("fa", "fas", "Persian"),
    ("fi", "fin", "Finnish"),
    ("fr", "fre", "French"),
    ("he", "heb", "Hebrew"),
    ("hi", "hin", "Hindi"),
    ("hr", "hrv", "Croatian"),
    ("ht", "hat", "Haitian Creole"),
    ("hu", "hun", "Hungarian"),
    ("id", "ind", "Indonesian"),
    ("is", "isl", "Icelandic"),
    ("it", "ita", "Italian"),
    ("ja", "jpn", "Japanese"),
    ("jv", "jav", "Javanese"),
    ("ko", "kor", "Korean"),
    ("lt", "lit", "Lithuanian"),
    ("lv", "lav", "Latvian"),
    ("mr", "mar", "Marathi"),
    ("ms", "msa", "Malay"),
    ("nl", "nld", "Dutch"),
    ("no", "nor", "Norwegian"),
    ("pa", "pan", "Punjabi"),
    ("pl", "pol", "Polish"),
    ("pt", "por", "Portuguese"),
    ("ro", "ron", "Romanian"),
    ("ru", "rus", "Russian"),
    ("sk", "slk", "Slovak"),
    ("sl", "slv", "Slovenian"),
    ("sr", "srp", "Serbian"),
    ("sv", "swe", "Swedish"),
    ("ta", "tam", "Tamil"),
    ("te", "tel", "Telugu"),
    ("th", "tha", "Thai"),
    ("tr", "tur", "Turkish"),
    ("uk", "ukr", "Ukrainian"),
    ("ur", "urd", "Urdu"),
    ("vi", "vie", "Vietnamese"),
    ("zh", "zho", "Chinese"),
]

# Curated LibriVox archive.org items (verified MP3 + language).
CURATED: dict[str, dict] = {
    "en": {
        "identifier": "stories_001_librivox",
        "title": "English — The Black Cat (excerpt)",
        "work": "The Black Cat",
        "author": "Edgar Allan Poe",
        "reader": "Phil Chenevert",
    },
    "fr": {
        "identifier": "contes_humoristiques_1505_librivox",
        "title": "French — La cafetière (excerpt)",
        "work": "La cafetière",
        "author": "Théophile Gautier",
        "reader": "Zeckou",
    },
    "es": {
        "identifier": "cuentos_ingenuos_2108_librivox",
        "title": "Spanish — Cuentos ingenuos (excerpt)",
        "work": "Cuentos ingenuos",
        "author": "Felipe Trigo",
        "reader": "Epachuko",
    },
    "de": {"identifier": "nicholasnickelbyband1_2409_librivox", "title": "German — Nicholas Nickelby Band 1 (excerpt)"},
    "it": {"identifier": "novelleperunanno_vol11_lagiara_1312_librivox", "title": "Italian — Novelle per un Anno: La Giara (excerpt)"},
    "pt": {"identifier": "o_ateneu_1012_librivox", "title": "Portuguese — O Ateneu (excerpt)"},
    "ja": {"identifier": "meguriai_1409_librivox", "title": "Japanese — めぐりあひ (excerpt)"},
    "ko": {"identifier": "animal_meeting_1509_librivox", "title": "Korean — Assembly of Animals (excerpt)"},
    "zh": {"identifier": "panghuang_1910_librivox", "title": "Chinese — 徬徨 (excerpt)"},
    "ru": {"identifier": "early_short_stories_jabotinsky_1410_librivox", "title": "Russian — Early Short Stories (excerpt)"},
    "pl": {"identifier": "lalkavol1_1405_librivox", "title": "Polish — Lalka tom 1 (excerpt)"},
    "nl": {"identifier": "duizend_en_een_nacht_4_1411_librivox", "title": "Dutch — Duizend en één Nacht (excerpt)"},
    "ar": {"identifier": "kitab_adab_dunya_1107_librivox", "title": "Arabic — Kitab Adab al-Dunya (excerpt)"},
    "hi": {"identifier": "dosakhiyan_2512_librivox", "title": "Hindi — Do Sakhiyan (excerpt)"},
    "he": {"identifier": "in_winter_ol_librivox", "title": "Hebrew — בחורף In Winter (excerpt)"},
    "hr": {"identifier": "prieizdavnine_1903_librivox", "title": "Croatian — Priče iz Davnine (excerpt)"},
    "ht": {"identifier": "toussaintlouverture_1203_librivox", "title": "Haitian Creole — Toussaint L'Ouverture (excerpt)"},
    "hu": {"identifier": "egri_csillagok_1101_librivox", "title": "Hungarian — Egri csillagok (excerpt)"},
    "id": {"identifier": "mengelilingi_doenia_dalam_80_hari_2212_librivox", "title": "Indonesian — Mengelilingi Doenia (excerpt)"},
    "is": {"identifier": "journey_into_the_interior_of_the_earth_2209_librivox", "title": "Icelandic — Journey into the Interior of the Earth (excerpt)"},
    "jv": {"identifier": "sekar_karya_0811_librivox", "title": "Javanese — Sekar Karya (excerpt)"},
    "lt": {"identifier": "jungle_tw_0908_librivox", "title": "Lithuanian — The Jungle (excerpt)"},
    "lv": {"identifier": "lacplesis_kb_librivox", "title": "Latvian — Lāčplēsis (excerpt)"},
    "bn": {"identifier": "hungry_stones_1205_librivox", "title": "Bengali — The Hungry Stones (excerpt)"},
    "bg": {"identifier": "epopeyanazabravenite_1608_librivox", "title": "Bulgarian — Епопея на Забравените (excerpt)"},
    "ca": {"identifier": "reculldecontes_2205_librivox", "title": "Catalan — Recull de contes (excerpt)"},
    "cs": {"identifier": "krysar_2007_librivox", "title": "Czech — Krysař (excerpt)"},
    "da": {"identifier": "klassiske_eventyr_librivox", "title": "Danish — Klassiske eventyr (excerpt)"},
    "el": {"identifier": "poiositonofoneus_2204_librivox", "title": "Greek — Ποίος ήτον ο φονεύς (excerpt)"},
    "eu": {"identifier": "christmas_carols_2012_librivox", "title": "Basque — Christmas Carol Collection (excerpt)"},
    "fa": {"identifier": "herodotus_histories_3_0912_librivox", "title": "Persian — Herodotus Histories Vol 3 (excerpt)"},
    "fi": {"identifier": "vaihodkas_mr_librivox", "title": "Finnish — Vaihdokas (excerpt)"},
    "no": {"identifier": "densisteviking_2001_librivox", "title": "Norwegian — Den siste viking (excerpt)"},
    "ro": {"identifier": "carteadeaur_2110_librivox", "title": "Romanian — Cartea de Aur (excerpt)"},
    "uk": {"identifier": "maskarad_2110_librivox", "title": "Ukrainian — Маскарад (excerpt)"},
    "sv": {"identifier": "nyckfull_kvinna_4_lr_librivox", "title": "Swedish — En Nyckfull kvinna (excerpt)"},
    "ta": {"identifier": "tiruppavai_nr_librivox", "title": "Tamil — Tiruppavai (excerpt)"},
    "te": {"identifier": "visha_vahini_1512_librivox", "title": "Telugu — Visha Vahini (excerpt)"},
    "ur": {"identifier": "ghazals_ghalib_0809_librivox", "title": "Urdu — Selected Ghazals of Ghalib (excerpt)"},
    "mr": {"identifier": "multilingual024-poetryprose_2006_librivox", "title": "Marathi — Multilingual Short Works 024 (excerpt)"},
    "sl": {
        "identifier": "multilingual_short_works_collection_011_1401_librivox",
        "title": "Slovenian — Multilingual Short Works 011 (excerpt)",
        "note": "LibriVox multilingual collection (Slovenian section)",
    },
    "sr": {
        "identifier": "msw041_2605_librivox",
        "file": "msw041_02_ostajteovdje_santic_gvm_64kb.mp3",
        "title": "Serbian — Ostajte ovdje… (excerpt)",
        "note": "LibriVox multilingual collection (Bosnian/Serbian)",
    },
}

# FLEURS fallback (CC BY 4.0) — sparse/no dedicated LibriVox on archive.org
FLEURS: dict[str, str] = {
    "et": "et_ee",
    "ms": "ms_my",
    "pa": "pa_in",
    "th": "th_th",
    "tr": "tr_tr",
    "vi": "vi_vn",
    "sk": "sk_sk",
}


def curl_json(url: str) -> dict:
    out = subprocess.check_output(["curl", "-sL", url], text=True)
    return json.loads(out)


def archive_search(iso2: str) -> dict | None:
    q = urllib.parse.urlencode(
        {"q": f"librivox language:{iso2}", "fl[]": "identifier,title,language", "rows": "1", "output": "json"}
    )
    d = curl_json(f"https://archive.org/advancedsearch.php?{q}")
    docs = d.get("response", {}).get("docs") or []
    return docs[0] if docs else None


def list_mp3(identifier: str) -> list[str]:
    meta = curl_json(f"https://archive.org/metadata/{identifier}")
    files = meta.get("files") or []
    mp3 = sorted(f["name"] for f in files if f.get("name", "").endswith("_64kb.mp3"))
    if not mp3:
        mp3 = sorted(f["name"] for f in files if f.get("name", "").endswith(".mp3"))
    return mp3


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["curl", "-sL", "-o", str(dest), url])


def run_ffmpeg(args: list[str]) -> None:
    subprocess.check_call(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args])


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    )
    return float(out.strip())


def to_aac(src: Path, dest: Path, offset: float, duration: float) -> float:
    run_ffmpeg(
        [
            "-ss",
            str(offset),
            "-i",
            str(src),
            "-t",
            str(duration),
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(dest),
        ]
    )
    return probe_duration(dest)


def resolve_archive(iso1: str, iso2: str, name: str) -> dict:
    if iso1 in CURATED:
        src = dict(CURATED[iso1])
        src.setdefault("license", "Public Domain")
        src.setdefault("source", "LibriVox / Internet Archive")
        return src
    if iso1 in FLEURS:
        return {
            "type": "fleurs",
            "fleurs": FLEURS[iso1],
            "title": f"{name} — FLEURS speech sample",
            "license": "CC BY 4.0",
            "source": "Google FLEURS (HuggingFace)",
        }
    doc = archive_search(iso2)
    if doc:
        return {
            "identifier": doc["identifier"],
            "title": f"{name} — {doc.get('title', 'LibriVox excerpt')[:60]} (excerpt)",
            "license": "Public Domain",
            "source": "LibriVox / Internet Archive",
        }
    return {"type": "missing"}


def fetch_fleurs(iso1: str, fleurs_code: str, tmp: Path) -> tuple[Path, str]:
    from datasets import load_dataset
    import numpy as np
    import soundfile as sf

    ds = load_dataset("google/fleurs", fleurs_code, split="train[:200]")
    pick = None
    for row in ds:
        audio = row["audio"]
        dur = len(audio["array"]) / audio["sampling_rate"]
        if 4.0 <= dur <= 12.0:
            pick = row
            break
    if not pick:
        pick = ds[0]
    audio = pick["audio"]
    wav = tmp / f"{iso1}-fleurs.wav"
    arr = np.array(audio["array"], dtype="float32")
    sf.write(str(wav), arr, audio["sampling_rate"])
    text = pick.get("transcription") or pick.get("raw_transcription") or ""
    return wav, text


def build_one(iso1: str, iso2: str, name: str, force: bool) -> dict:
    out_dir = AUDIO / iso1
    aac = out_dir / f"qa-{iso1}-001.aac"
    txt = out_dir / f"qa-{iso1}-001.txt"

    if aac.exists() and not force:
        dur = probe_duration(aac)
        spec = resolve_archive(iso1, iso2, name)
        return {
            "status": "skipped",
            "id": f"{iso1}-001",
            "iso639_1": iso1,
            "iso639_2": iso2,
            "file": f"{iso1}/qa-{iso1}-001.aac",
            "title": spec.get("title", f"{name} speech sample"),
            "source": spec.get("source", "LibriVox / Internet Archive"),
            "license": spec.get("license", "Public Domain"),
            "durationSec": round(dur),
            "originalUrl": spec.get("identifier") and f"https://archive.org/details/{spec['identifier']}" or "",
        }

    spec = resolve_archive(iso1, iso2, name)
    if spec.get("type") == "missing":
        return {"status": "missing"}

    with tempfile.TemporaryDirectory(prefix=f"qa-speech-{iso1}-") as td:
        tmp = Path(td)
        transcript = ""
        license_ = spec.get("license", "Public Domain")
        source = spec.get("source", "LibriVox / Internet Archive")
        title = spec.get("title", f"{name} speech sample")
        original_url = ""
        reader = spec.get("reader", "")

        if spec.get("type") == "fleurs":
            wav, transcript = fetch_fleurs(iso1, spec["fleurs"], tmp)
            raw = tmp / "raw.wav"
            # loop/extend short FLEURS clips to target length
            dur = probe_duration(wav)
            if dur < CLIP_SEC:
                loops = int(CLIP_SEC / dur) + 2
                run_ffmpeg(["-stream_loop", str(loops), "-i", str(wav), "-t", str(CLIP_SEC + 5), str(tmp / "extended.wav")])
                wav = tmp / "extended.wav"
            raw = wav
            offset = 0
            original_url = f"https://huggingface.co/datasets/google/fleurs"
        else:
            ident = spec["identifier"]
            original_url = f"https://archive.org/details/{ident}"
            mp3s = list_mp3(ident)
            if not mp3s:
                return {"status": "error", "error": f"No MP3 in {ident}"}
            pick = spec.get("file") or mp3s[min(2, len(mp3s) - 1)]
            url = f"https://archive.org/download/{ident}/{urllib.parse.quote(pick)}"
            raw = tmp / "raw.mp3"
            download(url, raw)
            total = probe_duration(raw)
            offset = min(OFFSET_SEC, max(0, total - CLIP_SEC - 1))

        out_dir.mkdir(parents=True, exist_ok=True)
        dur = to_aac(raw, aac, offset, CLIP_SEC)
        if transcript:
            txt.write_text(transcript.strip() + "\n", encoding="utf-8")

        entry = {
            "status": "ok",
            "id": f"{iso1}-001",
            "iso639_1": iso1,
            "iso639_2": iso2,
            "file": f"{iso1}/qa-{iso1}-001.aac",
            "title": title,
            "source": source,
            "license": license_,
            "durationSec": round(dur),
            "originalUrl": original_url,
        }
        if reader:
            entry["reader"] = reader
        if spec.get("note"):
            entry["fallbackNote"] = spec["note"]
        if transcript:
            entry["transcriptFile"] = f"{iso1}/qa-{iso1}-001.txt"
        if spec.get("type") == "fleurs":
            entry["fallback"] = "FLEURS"
        return entry


def write_manifest(samples: list[dict]) -> None:
    manifest = {
        "version": 2,
        "baseUrl": "https://raw.githubusercontent.com/lisa-langlois-daily/test-video-asset/main/audio/",
        "samples": [
            {k: v for k, v in s.items() if k not in ("status", "fallbackNote") and not k.startswith("_")}
            for s in samples
            if s.get("id")
        ],
    }
    (AUDIO / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_attribution(samples: list[dict]) -> None:
    lines = [
        "# Speech sample attribution",
        "",
        "Human speech tracks for QA Test Video Generator multi-audio testing.",
        "",
        "## Processing",
        "",
        "Each clip was trimmed (~20 s offset where applicable, ~35 s duration) and transcoded to **AAC 48 kHz stereo**.",
        "See `manifest.json` for per-file metadata and ffmpeg language tags (`iso639_2`).",
        "",
        "## Samples",
        "",
        "| Sample ID | Language | Title | Source | License |",
        "|-----------|----------|-------|--------|---------|",
    ]
    for s in sorted(samples, key=lambda x: x.get("iso639_1", "")):
        if not s.get("id"):
            continue
        note = f" ({s['fallbackNote']})" if s.get("fallbackNote") else ""
        fb = " **[FLEURS fallback]**" if s.get("fallback") else ""
        lines.append(
            f"| `{s['id']}` | {s.get('iso639_2', '')} | {s.get('title', '')}{note}{fb} | {s.get('source', '')} | {s.get('license', '')} |"
        )
    lines.extend(
        [
            "",
            "## Licenses",
            "",
            "- **LibriVox / Internet Archive:** Public Domain (LibriVox policy).",
            "- **Google FLEURS fallback** (et, ms, pa, sk, th, tr, vi): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — used where dedicated LibriVox recordings are unavailable on archive.org.",
            "",
        ]
    )
    (AUDIO / "ATTRIBUTION.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Rebuild existing samples")
    parser.add_argument("--lang", action="append", help="Only build these iso639-1 codes")
    args = parser.parse_args()

    targets = LANGS
    if args.lang:
        codes = set(args.lang)
        targets = [t for t in LANGS if t[0] in codes]

    results = []
    for iso1, iso2, name in targets:
        print(f"[{iso1}] building…", flush=True)
        try:
            r = build_one(iso1, iso2, name, args.force)
            r["iso639_1"] = iso1
            print(f"  -> {r.get('status', r)}", flush=True)
        except Exception as e:
            r = {"status": "error", "iso639_1": iso1, "error": str(e)}
            print(f"  -> ERROR {e}", flush=True)
        results.append(r)
        time.sleep(0.1)

    ok = [r for r in results if r.get("status") in ("ok", "skipped")]
    missing = [r["iso639_1"] for r in results if r.get("status") == "missing"]
    errors = [r for r in results if r.get("status") == "error"]

    # Load existing manifest entries for skipped langs
    manifest_path = AUDIO / "manifest.json"
    existing = {}
    if manifest_path.exists():
        existing = {s["iso639_1"]: s for s in json.loads(manifest_path.read_text()).get("samples", []) if "iso639_1" in s}

    samples = []
    for r in results:
        if r.get("id"):
            samples.append(r)
        elif r.get("status") == "skipped" and r["iso639_1"] in existing:
            samples.append(existing[r["iso639_1"]])

    write_manifest(samples)
    write_attribution(samples)

    print("\n=== Summary ===")
    print(f"OK/skipped: {len(ok)} / {len(targets)}")
    print(f"Missing: {missing}")
    print(f"Errors: {len(errors)}")
    for e in errors:
        print(f"  {e.get('iso639_1')}: {e.get('error')}")
    return 1 if missing or errors else 0


if __name__ == "__main__":
    sys.exit(main())
