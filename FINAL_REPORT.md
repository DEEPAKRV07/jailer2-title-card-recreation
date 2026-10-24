# Delivered render report

> Historical report for the original KARTHIKEYAN render. Filenames, text and settings below describe that earlier delivery, not the current defaults. Use [README.md](README.md) to run the project and [CONFIGURATION.md](CONFIGURATION.md) to edit it.

Rendered and verified on 24 October 2026.

- Master: output/KARTHIKEYAN_4K.mp4
- Container duration: 21.800000 seconds.
- Video: H.264, 3840 x 2160, 30/1 fps, 654 frames, yuv420p. Native 4K procedural rasterization; portrait texture derives from the supplied 1600 x 899 JPEG.
- Audio: AAC, 44,100 Hz, stereo, 21.800000-second container stream. Original content, zero offset, gain 0.65. Decoded AAC padding extends sample duration to 21.803537 seconds; no accumulating A/V drift.
- Master size: 17313046 bytes.
- Full-stream decode: passed; all metadata checks passed.
- Audio sample peak: 0.8788922429084778; zero decoded samples above full scale. Source alignment verified at zero offset.
- Supplied portrait asset copied byte-for-byte. Rendering does not read reference video pixels.
- Default text: K and KARTHIKEYAN. Unspecified credit fields remain empty; main name holds through their slots.

## Deliverables

- output/KARTHIKEYAN_4K.mp4
- previews/KARTHIKEYAN_preview.mp4 (1280 x 720, 654 frames, 21.8 s)
- previews/KARTHIKEYAN_portrait_reveal_preview.mp4 (1280 x 720, 271 frames, 9.033333 s); short preset was rendered and verified.
- previews/portrait_reveal_comparison.jpg (beginning/midpoint/end versus reference)
- previews/reviewed_contact_sheet.jpg and encoded_master_contact_sheet.jpg
- README.md, editable config.json, complete Python sources, Windows launchers and required still/audio assets
- analysis/input_metadata.json, scene_breakdown.md/.json, every-frame traces and dense sheets
- qa/visual_review.md, encoded_review.json, project_checks.json, metadata validations and command/log files
- ../KARTHIKEYAN_reusable_project.zip (includes master and previews; excludes redundant reference movies and downloaded executables)

## Actual visual review and limits

Initial, revised and native 4K stills were inspected before the master render; decoded-master samples were inspected afterward. Adjustments improved framing, jewel brightness, portrait contrast, star size and rain visibility. This is an inspected procedural approximation, not an exact match certification. Early rain remains finer/more evenly distributed than the original; the original particle trajectories, 3D star and optical gemstone treatment are approximated. The uploaded pose and shoulder proportions differ and were preserved. No new face was generated.

Only the full sequence was rendered at 4K in this delivery. The short preset has a verified 720p preview and a runnable 4K command. Windows batch launchers are provided; their Python entry points, tool discovery and rendering were exercised here, but a fresh Windows installation was not simulated.

## Integrity

Master SHA-256: 73ad4197b2d8abdf676fb4c7e67dcae001e332fcb87b4fc56f391d4949ad1082
