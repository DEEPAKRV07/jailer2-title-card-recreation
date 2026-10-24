# Procedural portrait title card renderer

Edit the existing `config.json` directly. Each portrait and title field remains independent, so you can change the image, opening letter, title text, subtitles, timings, fonts and credits without a second configuration file.

Run `preview.bat` to generate the current preview, inspect the stable `previews/current_*.png` frames and contact sheet, then run `render.bat` for the configured final output. Both launchers use only `config.json`, so preview and final render use the same settings.

The main editable sections are:

- `portrait.image`, `portrait.mask`, `portrait.crop`, `portrait.anchor` and portrait reveal settings.
- `opening.letter` and the opening timing fields.
- Every object in `titles[]`, including its `text`, `subtitle`, timing, font size, position and tracking.
- `typography`, `palette`, `effects`, `rain`, `particles`, `audio` and `output` for the remaining advanced controls.

Paths are relative to the project folder unless absolute. Windows paths with spaces are supported. Source portraits are never modified. For a new portrait, clear or update any old `portrait.mask` and `portrait.subject_polygon`. Without an explicit mask, polygon or usable source alpha, the renderer uses cached automatic foreground extraction. For manual control, set `portrait.mask` to a same-size grayscale image with white for the subject and black for the background.

Preview cleanup is restricted to generated files inside `previews/` and `qa/`, using content hashes and a checked manifest. Unknown or changed user files are preserved. Final rendering validates a temporary file before replacing the configured output.

The renderer uses CUDA through CuPy for particle equations, rasterization, image effects, compositing, temporal blur and colour conversion when a compatible GPU is detected, then tests and selects an available hardware encoder. A detected CUDA device that fails initialization stops with an actionable error. CPU-only operations are logged. See [PERFORMANCE.md](PERFORMANCE.md) and [IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md) for measured results and limitations.

The extended sequence is 21.8 seconds at 30 fps and the `portrait_reveal` preset is 271 frames. The current config outputs `output/DEEPAK R V.mp4` and `previews/DEEPAK_R_V_preview.mp4`.
