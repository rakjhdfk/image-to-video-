# Components and provenance

The production scripts use Pillow, NumPy and SciPy, with FFmpeg installed separately. Neural speech uses sherpa-onnx and the official MeloTTS English ONNX model.

- **Pillow:** HPND license; https://github.com/python-pillow/Pillow
- **NumPy:** BSD-3-Clause; https://github.com/numpy/numpy
- **SciPy:** BSD-3-Clause; https://github.com/scipy/scipy
- **sherpa-onnx:** Apache-2.0; https://github.com/k2-fsa/sherpa-onnx
- **MeloTTS:** MIT; https://github.com/myshell-ai/MeloTTS
- **FFmpeg:** licensing depends on the selected build. The cloud validation used a GPL-enabled build. No FFmpeg binary is bundled; see https://ffmpeg.org/legal.html.

`setup_audio.py` downloads the official model archive over verified HTTPS and checks pinned archive and model SHA-256 values. The model's license is retained with its files; the current production also retains a copy in `output/voices/MeloTTS_LICENSE.txt`.

`tool_compatibility.json` records the separately assessed ComfyUI, RIFE, Coqui and MuseTalk candidates, their sources and limitations. They are not installed or represented as enabled production backends.

The screenplay, procedural character drawings, score and sound effects were created for this project. Background artwork was generated for this production; `output/backgrounds/asset_manifest.json` records the actual image sources and crops. It is not a downloaded stock-art collection.

The six dialogue identities are processed profiles of one female Indian English neural speaker, not six independent actors. Consult `output/audio_report.json` and `output/quality_report.json` for material production limits.
