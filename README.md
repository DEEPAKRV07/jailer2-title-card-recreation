# Reusable portrait title animation

## Change only three settings

Open `user_config.json`, edit these values, and save:

```json
{
  "portrait_image": "assets/Cyberpunk Digital Rain Portrait.png",
  "display_name": "DEEPAK R V",
  "opening_letter": "D"
}
```

- `portrait_image`: image path, relative to this project folder. Spaces work. Absolute Windows paths can use forward slashes: `D:/Pictures/My Portrait.png`. In JSON, backslashes must be doubled.
- `display_name`: nonempty name for the main title. Long text auto-fits. Existing cards repeating the previous main name follow the new name; unrelated credits remain unchanged.
- `opening_letter`: exactly one letter or digit.

Double-click **preview.bat**, inspect `previews/`, then double-click **render.bat**. Both load the same three values. First-time setup installs dependencies automatically; Python 3.11+ and internet access are needed for setup.

`config.json` remains the advanced source for fonts, timing, particles, colours, audio, resolution and output paths. Overrides are applied in memory; the advanced file is never rewritten. Output filenames come from its existing paths, so the current DEEPAK video is named `output/PK_4K.mp4` and its preview is `previews/PK_preview.mp4`. Changing a name does not rename output paths.

## Portraits and previews

Place a new image in `assets/` and change its path in `user_config.json`. Source images are never modified. An old portrait polygon or mask is not applied to a different image. Transparent images use their alpha; other new images use cached automatic foreground extraction. Inspect the result: complicated backgrounds can require a custom mask. Optionally save a grayscale `<image-stem>.mask.png` beside the source, with white for the subject and black for the background, at the same dimensions. This adds no required setting.

Each preview run replaces inventoried generated preview and preview-QA files. Stable `current_*.png` frames and `current_contact_sheet.jpg` are extracted from that exact encoded preview. Cleanup is restricted to project `previews/` and `qa/` trees and checks stored content hashes. Unknown files, externally changed files, assets and final videos are preserved. An unknown file occupying a required output name produces an error instead of being overwritten. Historical final QA is retained separately from current preview QA. Final rendering validates a temporary MP4 before replacing the configured final destination.

## GPU processing

Setup detects CUDA hardware and installs project-local CuPy/CUDA dependencies. Rendering tests CUDA arithmetic and actual NVENC/QSV/AMF encoding, then logs the selected backend. A present CUDA GPU that fails initialization causes an error; it never silently switches to CPU. This machine uses its RTX 3050 for particle math/rasterization, image effects, blur, glow, compositing and colour conversion, then NVENC for H.264. The installed OpenCV build has no CUDA support; CuPy supplies image kernels.

CPU operations remain for image/file IO, Pillow glyph masks, cached GrabCut extraction, seeded PCG64 initialization, small timeline controls and audio/muxing. Systems without CUDA use the CPU renderer with an explicit reason; hardware encoders are still tested. Other compute APIs are detected, but this project currently implements its rendering kernels for CUDA only.

The existing CRF numbers map to NVENC CQ, using p7/hq and full-resolution multipass. These are different quality controls, so bitstreams and file sizes differ. Frame rate, resolution, duration and audio settings stay unchanged. New portraits require initial CPU extraction; first CUDA use also compiles kernels. Later runs reuse caches. See [PERFORMANCE.md](PERFORMANCE.md) for measurements and visual differences.

## Commands and troubleshooting

```bat
.venv\Scripts\python.exe main.py --preview
.venv\Scripts\python.exe main.py --render
.venv\Scripts\python.exe main.py --preset portrait_reveal --preview
.venv\Scripts\python.exe main.py --preset portrait_reveal --render
```

The extended sequence is 21.8 seconds at 30 fps; the short preset is 271 frames with matching original audio. Final resolution remains 3840 x 2160; previews are 1280 x 720. Short-preset filenames get a `_portrait_reveal` suffix.

For a missing image, check its spelling and extension, and resolve relative paths from this project folder. JSON requires double quotes and no trailing comma. For CUDA dependency failures, rerun `setup.bat`. Driver/runtime failures stop the program with details. A CuPy CUDA_PATH warning alone is not a failure: successful arithmetic tests and runtime logs establish whether the packaged runtime works.

`qa/preview_run.json` and `qa/final_run.json` record effective settings, hardware tests and executed CUDA operations. Validation includes full video decoding. [IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md) lists changes and executed tests. `FINAL_REPORT.md` is historical documentation for the original version.

This remains a procedural approximation of the reference. A still cannot supply new facial detail or hidden geometry. CPU/GPU interpolation and particle sampling differ slightly; exact pixel identity is not claimed. Reference footage is not copied into rendered frames.

