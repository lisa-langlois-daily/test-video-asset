# Speech sample attribution

All samples are **real human speech** from [LibriVox](https://librivox.org/) volunteer readings of public-domain texts, hosted on [Internet Archive](https://archive.org/). LibriVox dedicates its recordings to the **public domain**.

| Sample ID | Language | Work | Author | Reader | Archive item |
|-----------|----------|------|--------|--------|--------------|
| `en-001` | English (`eng`) | *The Black Cat* (excerpt) | Edgar Allan Poe | Phil Chenevert | [stories_001_librivox](https://archive.org/details/stories_001_librivox) |
| `fr-001` | French (`fre`) | *La cafetière* (excerpt) | Théophile Gautier | Zeckou | [contes_humoristiques_1505_librivox](https://archive.org/details/contes_humoristiques_1505_librivox) |
| `es-001` | Spanish (`spa`) | *Cuentos ingenuos* (excerpt) | Felipe Trigo | Epachuko | [cuentos_ingenuos_2108_librivox](https://archive.org/details/cuentos_ingenuos_2108_librivox) |

## Processing

Each clip was trimmed (~20 s offset, ~35–39 s duration) and transcoded to **AAC 48 kHz stereo** for QA test video generation. See `manifest.json` for file paths and ffmpeg language tags (`iso639_2`).

## License

Public Domain (LibriVox policy). No attribution is legally required; this file is provided for transparency and QA traceability.
