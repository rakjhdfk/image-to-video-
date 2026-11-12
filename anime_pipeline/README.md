# THE MAGICAL WORLD · Episode 1

A resumable production project for **The Boy Without a Magic Signature**. The episode follows ten consecutive one-minute story sections, with stable character identities, independently animated character rigs, English dialogue, original music, magical effects and chronological shot assembly.

The local renderer uses **Mode 2: lightweight hybrid animation**. It is a procedural anime-inspired production approach; it is not a claim of diffusion-generated, hand-drawn studio animation. The current cloud machine is Linux with CPU rendering. Windows 11 operation and the requested GTX 1660 hardware are separate validation targets and must not be described as tested here.

The generated episode uses independently moving 2D character rigs, drawn environments and timed magical effects. It falls short of the requested premium hand-painted anime appearance and natural character acting. These visual targets are limitations, even when the technical video checks pass.

## Windows installation

1. Install 64-bit [Python 3.12 or newer](https://www.python.org/downloads/windows/), including Tcl/Tk and the Python launcher. The audio-model installer uses Python 3.12's safe archive-extraction support.
2. Obtain a full FFmpeg build with the **rubberband** audio filter using the official [download page](https://ffmpeg.org/download.html#build-windows). Check the selected distributor's checksum or signature before extracting it, and add the directory containing `ffmpeg.exe` and `ffprobe.exe` to `PATH`. Keep verification enabled.
3. Open PowerShell in this directory and create an environment:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ffmpeg -version
   ffprobe -version
   ffmpeg -hide_banner -filters | Select-String rubberband
   python setup_audio.py
   ```

4. Start the interface with `python app.py` from the activated environment. `launch_windows.bat` prefers the project's `.venv` when present.

The requirements include Pillow, NumPy and SciPy, plus **sherpa-onnx 2.0.1** and **soundfile 0.14.0** for CPU neural speech. `setup_audio.py` downloads the approximately 163 MB official MeloTTS ONNX model archive from the sherpa-onnx GitHub release and verifies pinned archive/model checksums. It checks FFmpeg's rubberband filter and preserves existing model files if verification fails. Do not bypass the checksum or TLS checks. The first install needs Internet access; later speech generation can use the retained model locally.

The selected neural model exposes an **EN_INDIA** speaker, and an Indian English sample was exercised in this cloud environment. All six character identities are processed profiles of that **one female Indian English neural speaker**. Pitch, rate and effects distinguish them; these are not six independently cast, naturally expressive actors. Listen to the sample and review the voice report before accepting vocal identity or acting quality. Windows audio runtime compatibility still requires testing on the target machine.

Only compatible tools actually used by the configured production mode should be installed. ComfyUI, RIFE, Coqui TTS and MuseTalk are candidate projects, not assumed dependencies or installed integrations. Any neural model requires a separate license, memory, platform and sample-output check. Mode 1 and Mode 3 remain unavailable until a compatible backend has explicitly been configured and validated; remote execution is not invoked automatically.

## Run the production

Use the GUI buttons or the matching CLI commands:

```text
python pipeline.py prepare
python pipeline.py sample
python pipeline.py all --workers 2
python pipeline.py validate
```

Run `python setup_audio.py` before these commands. Generate and inspect a real end-to-end sample before beginning a full render. Review the character references, actual voices, animation, music, effects and quality report. The requested natural Indian English acting remains a perceptual validation target; the EN_INDIA speaker selection alone does not prove pronunciation or performance quality. Read the selected backend and limitations in the generated reports.

The direction-notes field is stored in `output/user_settings.json`. This project generates the fixed ten-section Episode 1 story. It does not offer unrestricted text-to-film generation. Palette settings and the selected production mode are saved alongside the notes.

## Pause, resume and regenerate

**Pause** creates `output/PAUSE`. The renderer should stop or wait at a safe checkpoint; the GUI does not kill an encoder in the middle of writing a shot. **Resume** removes the sentinel and resumes the existing worker or starts `all` again. Completed checkpoints are reused according to the pipeline's cache and validation rules.

Keep the GUI open while its worker is active, including while paused. Closing is refused with a warning because a pause keeps the generation process alive. Resume in the same window and wait for that command to finish before closing. A cross-platform production lock prevents a second GUI or CLI command from starting a duplicate production job. `python pipeline.py resume` releases the pause for an already active job rather than launching another worker.

```text
python pipeline.py pause
python pipeline.py resume
python pipeline.py render --shot 17 --force
python pipeline.py audio
python pipeline.py export
python pipeline.py validate
```

Shot indices run from `0` to `59`. After regenerating any selected shot or dialogue, run `export` and `validate` again. The interface displays values read from `output/progress.json` and the actual subprocess log, including failures. It does not simulate rendering progress or report unexecuted work as complete.

The default full render uses **two shot workers**, with two encoder threads per worker. This bounds concurrency for the six-core laptop; use `--workers 1` if memory pressure or other workloads make two workers unsuitable. Keep the project, generated voices and checkpoints on the SSD. Each completed shot has an MP4 in `output/renders/` and a fingerprint/state file in `output/animation/`; matching completed shots are reused, while changed input or code invalidates the relevant cache. Preserve both directories when moving or backing up the project. Incomplete temporary encodes are not completed checkpoints.

## Output files

Generated production media and reports are under `output/`:

- `THE_MAGICAL_WORLD_EP01_720P.mp4`: final episode, when successfully exported.
- `sample.mp4`: end-to-end sample, when generated.
- `episode01_screenplay.json` and `episode01_timeline.json`: editable shot plan and per-second timeline.
- `episode01_storyboard/`, `characters/`, `backgrounds/`, `animation/` and `renders/`: production assets and shot checkpoints.
- `voices/`: individual dialogue recordings; `music/` and `sound_effects/`: audio stems.
- `quality_report.json`: technical checks and material quality limitations.
- `generation_log.txt`: actual production log.

The interface can export existing dialogue, music or effect files as ZIP archives. It refuses to create an apparently successful audio export when the corresponding folder contains no generated audio. **Play sample**, **Play episode** and **Open Output Folder** use the computer's local applications; this does not require the chat's artifact downloader.

### Master and delivery copy

`output/THE_MAGICAL_WORLD_EP01_720P.mp4` is the full-quality local master, approximately 206 MiB for this production. A smaller encode is stored at `delivery/THE_MAGICAL_WORLD_EP01_720P.mp4` for source-package distribution. The delivery encode retains the same complete 600-second timeline, 1280×720 resolution and 24 FPS, with stronger video compression. The large master and intermediate renders need not be included in a source package.

**Play episode** first opens the local output master. If that file is absent, it opens the delivery copy instead. This makes a distributed source package playable without rerendering the episode or installing the speech model. Regeneration still requires the setup steps above and generates a new local master. Review the final quality report for the checks actually executed; delivery and publication are separate from successful local rendering.

## Validation and practical limits

The required final target is exactly **600 seconds, 1280×720, 24 FPS, 14,400 video frames, H.264 video and AAC audio at 48 kHz**. The report must distinguish rendered assets, missing shots, missing speech, failed checks, unsupported capabilities and unverified visual targets. A technically valid container alone does not prove premium anime quality, natural Indian English, believable acting or seamless combat choreography.

Keep the project and its generated checkpoints on the SSD. Review the actual machine's free memory and GPU before adding a model. Large video diffusion models are optional, and are not a requirement for the lightweight mode. Avoid interpolation across incompatible drawings or shot boundaries.
