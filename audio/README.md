# QA speech samples

Human speech audio tracks for the [QA Test Video Generator](https://github.com/lisa-langlois-daily/qa-test-video-generator) n8n workflow (QA-15991 multi-audio).

## Format

- **Codec:** AAC-LC
- **Sample rate:** 48 kHz
- **Channels:** stereo
- **Duration:** ~35–39 s per file (looped/trimmed at runtime to match video length)

## Manifest

`manifest.json` lists every sample with:

- `id` — referenced by n8n presets (`sampleId`, e.g. `en-001`)
- `iso639_1` / `iso639_2` — language codes (`eng`, `fre`, `spa` for ffmpeg `-metadata:s:a:N language=…`)
- `file` — path relative to this folder

## Raw URL pattern

```
https://raw.githubusercontent.com/lisa-langlois-daily/test-video-asset/main/audio/{file}
```

Example: `https://raw.githubusercontent.com/lisa-langlois-daily/test-video-asset/main/audio/en/qa-en-001.aac`

## Adding samples

1. Add AAC file under `en/`, `fr/`, `es/`, etc.
2. Update `manifest.json` with a new `id` and metadata.
3. Add attribution row in `ATTRIBUTION.md`.
4. Sync presets in `qa-test-video-generator/code/audio-presets.js`.

Prefer real human speech with clear CC0 / Public Domain license (LibriVox, Mozilla Common Voice validated clips, etc.).
