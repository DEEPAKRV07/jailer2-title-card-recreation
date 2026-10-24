# Implementation report — three settings and GPU rendering

Project: `D:/boys-ai-videos/portrait_title_project`

Normal users edit only `portrait_image`, `display_name`, and `opening_letter` in `user_config.json`. The initial requested values are the Cyberpunk Digital Rain Portrait image, DEEPAK R V and D. Run preview.bat, inspect previews, then render.bat.

## Files created and modified

| File | Change |
|---|---|
| user_config.json | Exactly the three user settings |
| user_settings.py | Shared validation and in-memory overrides, safe image paths, optional mask sidecars |
| portrait_source.py | Nondestructive image loading, automatic/explicit masks, content-addressed foreground cache |
| renderer.py | Shared source preparation; existing animation equations retained |
| gpu_ops.py | CUDA image, raster, filter and colour conversion operations |
| gpu_renderer.py | GPU particle/vector operations using existing animation structure and parameters |
| hardware.py | GPU/API detection, CUDA arithmetic test, real NVENC/QSV/AMF probes, strict selection, dependency setup |
| requirements-gpu.txt | Project-local CuPy and minimal CUDA runtime/compiler dependencies |
| main.py | Shared preview/final settings, GPU rendering/encoding, current encoded preview frames, run telemetry and validation |
| generated_outputs.py | Hash-inventoried, directory-contained cleanup with user-file preservation |
| preview.bat / render.bat | Explicitly load user_config.json |
| setup_tools.py | Automatic GPU dependency setup |
| qa_encoded.py | Shared effective settings and generated QA inventory |
| remux_audio.py | Configured output paths instead of original hardcoded name |
| package_project.py | Generic current-project ZIP, current final and verification evidence |
| README.md / PERFORMANCE.md / this report | Workflow, measured results, limits |
| development/ scripts and reports | Frozen baseline, profiling, actual behavioral tests, comparison and final verification |

The advanced config was never rewritten by implementation or test code. External PK edits observed during the session were preserved. Its post-edit SHA-256 remained `4fbcafecaeabc11f4d5f037d5a7321e60b0d6d384f4034952a570d469829af87` across integration tests and final verification. The earlier frozen configuration exists only for equal-work benchmarking.

## Cleanup behavior

Preview and preview-QA manifests list generated paths and SHA-256 hashes. At the next preview, all paths are checked for containment before any removal. Only unchanged inventoried generated artifacts are deleted. Unknown or externally changed files are preserved; conflicting filenames stop generation with a readable error. A one-time explicit inventory covers the old known preview artifacts. No wildcard directory deletion is used. Final MP4s, source assets, scripts and configuration are outside this cleanup.

Stable current frame names and the contact sheet are extracted from the just-encoded preview, eliminating stale mixtures. Historical final QA is retained. Final rendering validates its pending file before replacing the configured final video. The previous PK final was copied to `development/preserved_outputs/PK_4K_before_template.mp4` before the requested new render; the other existing finals remain intact.

## Executed tests

`development/test_template.py` completed **24 passing checks**, recorded in `development/template_test_results.json`:

- Exactly three settings load and unrelated advanced animation parameters stay unchanged.
- Alternate letter/name change actual GPU frames; text changes leave the portrait unchanged.
- A different supplied source image changes the portrait; filenames with spaces, absolute Windows paths and optional mask sidecars work.
- Old polygons are not reused for a different image.
- Invalid JSON, empty name, invalid/multiple-character letter and missing source produce readable errors.
- Two actual full preview runs with different names/letters replace generated artifacts at stable filenames and produce fresh title pixels.
- Unknown sentinel files in preview/QA, all source asset hashes, existing final hashes and both configuration files remain unchanged during preview tests.
- Both presets produce actual GPU frames; the short preset completed a full 271-frame preview with audio and decode validation.
- Unsafe cleanup traversal is rejected.

Additional executed checks:
- CUDA arithmetic and all three FFmpeg hardware encoder probes.
- Actual before/after full-sequence CPU/GPU preview and 4K renders; see PERFORMANCE.md.
- Normal current 4K final rendered successfully; 654 frames executed on CUDA and NVENC confirmed in logs.
- Preview/final effective configuration fingerprints match exactly.
- Seven final encoded frames compared numerically to CUDA source frames; contact sheets visually inspected.
- setup_tools.py completed; modified runtime modules compile successfully.
- Four simulated backend/error checks passed: broken CUDA stops without CPU fallback, absent hardware gives an explicit CPU reason, unavailable hardware encoding selects libx264, and AMF encoding remains usable without CUDA compute. Actual NVIDIA rendering is verified separately in runtime logs.

## Delivered result and limitations

The current final is `output/PK_4K.mp4`, with DEEPAK R V and D inside. Its filename deliberately follows unchanged advanced config. The current viewing copy is `previews/PK_preview.mp4`. Both have the same source image and settings. Current final validation and hardware evidence are in qa/final_run.json and qa/PK_4K_validation.json.

GPU acceleration is confirmed on this machine, including actual rendering rather than just encoding. New-image foreground extraction and the documented unsupported operations remain CPU work. CUDA is the only implemented GPU compute API; AMD-only/Intel-only systems receive an explicit CPU-render reason while still trying hardware encoding. Exact CPU/GPU particles and hardware/software encoder bitstreams differ. These limitations and warm-cache timing conditions are detailed in PERFORMANCE.md.

Automatic foreground extraction is not universally reliable; the optional sidecar mask provides a correction without changing the three user settings. Rendering remains based on the supplied still, so missing geometry/detail and the original reference's exact optical effects cannot be recovered.

