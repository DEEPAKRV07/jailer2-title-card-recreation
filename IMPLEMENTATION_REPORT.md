# Implementation report — config-driven GPU rendering

For current run commands, see [README.md](README.md). For editable fields, see [CONFIGURATION.md](CONFIGURATION.md). Verification below records completed runs, not later configuration edits.

The project now uses the original `config.json` workflow. Each title card remains independently editable in `titles[]`; there is no secondary user configuration layer.

## Files created and modified

| File | Change |
|---|---|
| portrait_source.py | Nondestructive image loading, automatic/explicit masks, content-addressed foreground cache |
| renderer.py | Shared source preparation; existing animation equations retained |
| gpu_ops.py | CUDA image, raster, filter and colour conversion operations |
| gpu_renderer.py | GPU particle/vector operations using existing animation structure and parameters |
| hardware.py | GPU/API detection, CUDA arithmetic test, real NVENC/QSV/AMF probes, strict selection, dependency setup |
| requirements-gpu.txt | Project-local CuPy and minimal CUDA runtime/compiler dependencies |
| main.py | Shared preview/final settings, GPU rendering/encoding, current encoded preview frames, run telemetry and validation |
| generated_outputs.py | Hash-inventoried, directory-contained cleanup with user-file preservation |
| preview.bat / render.bat | Run only against config.json |
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

The current config-only verification compiled the modified runtime, generated preview frames from `config.json` on CUDA, and exercised the title fields independently. The earlier three-setting integration harness was removed with the override layer so it cannot become a stale second configuration path.

Additional executed checks:
- CUDA arithmetic and all three FFmpeg hardware encoder probes.
- Actual before/after full-sequence CPU/GPU preview and 4K renders; see PERFORMANCE.md.
- Normal current 4K final rendered successfully; 654 frames executed on CUDA and NVENC confirmed in logs.
- Preview/final effective configuration fingerprints match exactly.
- Seven final encoded frames compared numerically to CUDA source frames; contact sheets visually inspected.
- setup_tools.py completed; modified runtime modules compile successfully.
- Four simulated backend/error checks passed: broken CUDA stops without CPU fallback, absent hardware gives an explicit CPU reason, unavailable hardware encoding selects libx264, and AMF encoding remains usable without CUDA compute. Actual NVIDIA rendering is verified separately in runtime logs.

## Delivered result and limitations

The repository includes the example final `output/DEEPAK R V.mp4`, validated in `qa/DEEPAK R V_validation.json`. New renders follow `output.path` in `config.json` (committed default: `output/DEEPAKRV.mp4`); previews follow `output.preview_path`. Per-run hardware evidence is written to `qa/final_run.json` or `qa/preview_run.json`. Those reports describe their recorded run and may refer to an earlier output/configuration.

GPU acceleration is confirmed on this machine, including actual rendering rather than just encoding. New-image foreground extraction and the documented unsupported operations remain CPU work. CUDA is the only implemented GPU compute API; AMD-only/Intel-only systems receive an explicit CPU-render reason while still trying hardware encoding. Exact CPU/GPU particles and hardware/software encoder bitstreams differ. These limitations and warm-cache timing conditions are detailed in PERFORMANCE.md.

Automatic foreground extraction is not universally reliable; a custom mask selected through `portrait.mask` in `config.json` provides a correction. Rendering remains based on the supplied still, so missing geometry/detail and the original reference's exact optical effects cannot be recovered.

