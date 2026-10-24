# Performance and GPU verification — 24 October 2026

## Measured comparison

Both runs rendered the full 654-frame, 21.8-second sequence with the same frozen animation configuration, portrait, D opening and DEEPAK R V titles. CPU uses the saved original renderer; GPU uses CUDA and NVENC.

| Render | Before: original CPU | After: GPU, warm caches | Speedup |
|---|---:|---:|---:|
| 1280 x 720 preview | 132.152 s | 37.182 s | 3.55x |
| 3840 x 2160 final | 494.597 s | 85.633 s | 5.78x |

These are measured wall times, including renderer initialization, encoding, audio muxing and full decode validation. They exclude environment installation, hardware probing and contact-sheet extraction. They are individual runs, not statistical averages. Evidence: `development/benchmarks/cpu_times.json`, `gpu_times.json`, `baseline_effective_config.json`, and corresponding logs/validation JSON. Reproduce with `development/measure_baseline.py` and `development/measure_gpu.py`.

**Cache qualification:** the original renderer repeats GrabCut on every run. The updated pipeline caches this unsupported CPU operation and reuses warmed CUDA kernels. The table measures the combined implementation improvement, not isolated GPU compute speedup. Initial extraction of the current source measured **75.465 s**; a fresh portrait and first CUDA compilation add time. Caches are excluded from the reusable ZIP.

During work, advanced configuration was edited to a PK portrait with only one nonempty main title. Those edits were preserved, and the three requested overrides applied on top. Benchmarks deliberately use the frozen earlier configuration with repeated name cards so both sides have equal work. The current normal CLI outputs took **22.317 s preview** and **78.978 s final**, but those times are not used in the before/after speedup calculation.

## Profile and implementation

The original 4K profile recorded 82.810 s initialization, including 75.640 s in GrabCut, 76.921 s total portrait preparation and 5.546 s in four text preparations. Twelve sampled frames took 6.788 s. Whole-frame composition, text texture/reveal, portrait effects and thousands of particle easing/drawing operations were the repeatable CPU costs. Full cProfile output is in `development/benchmarks/cpu_profile.txt`.

CUDA now executes particle trajectories and gates, batched line/circle/ellipse/polygon rasterization, affine image transforms, resampling, grayscale, contrast/texture math, Sobel edges, morphology, Gaussian blur/glow, text material/reveal, layer composition, temporal blur and RGB-to-NV12 conversion. Particle drawing preserves last-draw overwrite order using an owner buffer. The GPU frame is transferred to FFmpeg for NVENC encoding; this is not a zero-copy pipeline.

CPU remains for disk/image IO, Pillow/FreeType glyph masks, cached OpenCV GrabCut, PCG64 seeded random initialization, small timeline/control/coefficient calculations, and AAC/muxing. These preserve the existing APIs and seeded behavior. OpenCV in this environment has no CUDA implementation of GrabCut. No CPU frame rendering is used on the detected NVIDIA GPU.

## Runtime evidence

Detected: **NVIDIA GeForce RTX 3050 6GB Laptop GPU**, 6144 MiB, compute capability 8.6, driver 591.74. CuPy 14.2.0 executes with CUDA runtime 12.9 and driver API 13.1. The installed OpenCV reports zero CUDA devices; OpenCL is available. The renderer uses its explicit CuPy implementation rather than assuming that OpenCV calls run on a GPU.

Actual two-frame H.264 encoder probes passed for NVENC and AMD AMF; QSV failed. NVIDIA NVENC was selected. A missing/broken CUDA runtime on a detected CUDA device causes an actionable error, with CPU fallback disabled. Other machines are probed at runtime; CUDA is the implemented compute API, so non-CUDA GPUs currently support encoding where available, not these rendering kernels.

The current final `qa/final_run.json` records 654 GPU frames and 43,232.931 ms of CUDA-event frame execution, including:
- 2,195 image sampling calls; 655 Gaussian operations; Sobel and morphology.
- 776 primitive raster calls and 290 particle equation calls.
- 654 composites, 653 temporal blur calls and 654 RGB-to-NV12 conversions.
- 325 text reveal calls.

CUDA-event frame time is not total wall time and excludes initialization and finish-frame work outside the timed frame method. The old benchmark JSON's global counters are cumulative across its preview/final pair; the current run records per-instance operation counts. FFmpeg's `qa/final_encode.log` and `final_commands.json` independently confirm h264_nvenc use.

## Quality and limits

No animation parameter, font, resolution, frame rate, scene duration or audio setting was changed in advanced config. NVENC uses p7/hq, full-resolution multipass and CQ 17 final/CQ 20 preview. Hardware CQ and software x264 CRF are not mathematically equivalent; this necessarily changes encoder controls and bitstreams. The later explicit GPU-encoding requirement takes precedence over keeping libx264 selected at runtime; config.json itself still retains the original encoder fields.

CPU/GPU comparison frames and encoded preview/final contact sheets were actually inspected. The opening letter, title, facial proportions, settled portrait and composition remain consistent. At 9.6 s the CPU/GPU raw-frame PSNR was 45.04 dB; the held letter at 2.9 s was identical. During the 7.8 s reveal, PSNR was 17.76 dB because small interpolation/weight changes alter individual sampled particle positions. Exact trajectories and pixel identity are not promised. See `development/benchmarks/cpu_gpu_comparison.jpg` and `gpu_pixel_comparison.json`.

Seven final encoded frames were compared against CUDA source frames with the same temporal blending. PSNR ranged **44.59–55.39 dB**, mean absolute channel errors **0.098–0.520 / 255**. These samples support compression quality, not proof about every pixel of the sequence. Beginning/middle/end reveal samples and the final title were visually inspected in `development/verification/final_contact_sheet.jpg`.

All final metadata checks and full decode passed: 3840 x 2160, 30 fps, 654 frames, 21.8 s, H.264 yuv420p, stereo AAC 44.1 kHz. Audio offset, gain and fades follow the existing advanced configuration.

Implementation references: [CuPy installation and CUDA packages](https://docs.cupy.dev/en/stable/install.html), [NVIDIA Video Codec SDK](https://developer.nvidia.com/video-codec-sdk). All timing and hardware claims above come from this project's runtime evidence, not vendor performance estimates.

