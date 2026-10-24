# Jailer 2 title card recreation

Procedural portrait and title animation built with Python, NumPy, OpenCV, Pillow, CuPy and FFmpeg. Generate a sparkling opening letter, digital rain, a particle-driven portrait reveal and independently editable title cards. The source portrait supplies the face and clothing; reference footage is not copied into rendered frames.

All settings live in **`config.json`**. There is no secondary user-config file or automatic name override.

## Quick start on Windows

Use 64-bit Windows and Python 3.11 (tested with 3.11.9), with **Add Python to PATH** enabled. First-time setup needs internet access, a writable project folder and disk space for dependencies/videos. CUDA rendering requires a compatible NVIDIA GPU and driver; other systems use CPU rendering with an explicit logged reason.

1. Download with **Code > Download ZIP** and extract, or clone:

   ```powershell
   git clone https://github.com/DEEPAKRV07/jailer2-title-card-recreation.git
   cd jailer2-title-card-recreation
   ```

2. Open PowerShell in the project folder and set up dependencies:

   ```powershell
   .\setup.bat
   ```

   Setup creates `.venv`, installs pinned packages, prepares FFmpeg/ffprobe and installs CUDA dependencies when an NVIDIA device is detected. If ffprobe is missing, setup downloads the Windows FFmpeg essentials archive. Rerun setup to resume an interrupted download.

3. Edit `config.json`: change `portrait.image`, `opening.letter`, each card in `titles[]` and the output paths. See [CONFIGURATION.md](CONFIGURATION.md) for the complete editing guide.

4. Generate a preview and inspect the video and `previews/current_contact_sheet.jpg`:

   ```powershell
   .\preview.bat
   ```

5. When satisfied, render the final video:

   ```powershell
   .\render.bat
   ```

You can also double-click the batch files. Preview/render launchers run setup if `.venv` is missing. No virtual-environment activation is required.

After pulling an update, rerun `setup.bat` before previewing or rendering so an existing environment receives any new dependencies, including Unicode font coverage support.

## Outputs and manual commands

The committed config produces a 1280 × 720 preview and 3840 × 2160 final at 30 fps. The extended sequence is 21.8 seconds. Filenames come from `output.preview_path` and `output.path`; changing a title does not rename files.

- Configured preview: [previews/DHANUSH_preview.mp4](previews/DHANUSH_preview.mp4).
- Configured final: [output/DHANUSH.mp4](output/DHANUSH.mp4).
- Separately included example: [output/DEEPAK R V.mp4](output/DEEPAK%20R%20V.mp4).

The current example uses a centered portrait, opening `D`, `NADIPU ★ ASURAN` and a later `DHANUSH` card. Symbols use per-character fallback fonts while preserving the jeweled material. Supported single-character emoji render in monochrome; see [CONFIGURATION.md](CONFIGURATION.md) for the font list and limitations.

Run from the project folder after setup:

```powershell
# Preview video and frames extracted from that encoded video
.\.venv\Scripts\python.exe main.py --config config.json --preview

# Final render with metadata and full-decode validation
.\.venv\Scripts\python.exe main.py --config config.json --render

# Still frames only; refreshes the generated preview set
.\.venv\Scripts\python.exe main.py --config config.json --frames

# Short portrait preset: 271 frames, about 9.03 seconds
.\.venv\Scripts\python.exe main.py --config config.json --preset portrait_reveal --preview
.\.venv\Scripts\python.exe main.py --config config.json --preset portrait_reveal --render

# Command-line options
.\.venv\Scripts\python.exe main.py --help
```

The short-preset CLI adds `_portrait_reveal` to the output filenames. Successful renders print `Render verified`. `qa/preview_run.json` and `qa/final_run.json` record the effective settings, device, encoder, elapsed time and telemetry. Per-output validation reports are also saved in `qa/`.

Preview runs refresh only inventoried generated preview/QA files whose hashes still match. Unknown or changed files are preserved; a conflicting filename stops the run. Final rendering validates a temporary file before replacing the configured final video. Choose another output path to keep an earlier render.

## GPU support

Runtime detection tests CUDA arithmetic and actual NVENC, QSV and AMF encoding. Compatible NVIDIA devices use CuPy CUDA kernels for particles, rasterization, filtering, glow, compositing and colour conversion. A detected CUDA device that cannot initialize causes an error rather than silent CPU fallback.

GPU compute currently supports **CUDA only**. AMD/Intel-only systems use CPU rendering and may still use AMF/QSV encoding. Encoder selection is automatic: NVENC, QSV, AMF, then libx264, choosing the first successful runtime probe. `output.encoder` does not force the actual backend. Hardware CQ and software CRF are different controls, so bitstreams differ.

File/image IO, Pillow glyph masks, foreground extraction and other unsupported operations remain on CPU. [PERFORMANCE.md](PERFORMANCE.md) records measured results on the tested machine, not a speed guarantee for every GPU.

## Troubleshooting

| Problem | Action |
|---|---|
| Python is missing or opens the Microsoft Store | Install 64-bit Python with PATH enabled, reopen the terminal and check `python --version`. |
| Dependency installation fails | Use the tested Python 3.11 environment, read the installation error and rerun `setup.bat`. |
| CUDA initialization fails | Rerun `setup.bat`; check the GPU driver and printed runtime error. Detected CUDA hardware failing initialization deliberately stops the program. |
| FFmpeg/ffprobe is missing | Rerun setup. It checks for ffprobe on PATH or downloads the Windows essentials build into `tools/`. |
| Invalid JSON | Use double quotes, no comments/trailing commas and forward slashes in Windows paths. |
| Old masking affects a new portrait | Clear/update `portrait.mask` and `portrait.subject_polygon`, then inspect the preview. |
| Fonts are missing | Set `typography.font` and `typography.fallback_font` to existing font files. The defaults use Windows Georgia Bold and Times New Roman Bold. |
| A generated path conflicts with a user file | Back up/move the conflicting file or choose a different configured path. |
| GPU memory is insufficient | Close other GPU-heavy applications. Reducing resolution or supersampling is an optional change to output settings/quality. |

Reference videos are optional and omitted from the repository. For comparison sheets, place them in the sibling `title_card_reference_upload_pack` folder as `lv_0_20261021030852.mp4` and `reference video.mp4`. Normal rendering/previews work without them.

A still image cannot provide a different pose, hidden geometry or missing facial detail. The optical effects are procedural approximations.

## Documentation

- [CONFIGURATION.md](CONFIGURATION.md): portrait, independent titles, audio, timings and paths.
- [IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md): implementation and recorded verification.
- [PERFORMANCE.md](PERFORMANCE.md): historical CPU/GPU measurements and evidence.
- [FINAL_REPORT.md](FINAL_REPORT.md) and `development/baseline/`: historical snapshots, not current setup instructions.
