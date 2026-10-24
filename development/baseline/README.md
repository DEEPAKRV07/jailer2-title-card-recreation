# KARTHIKEYAN — procedural portrait title sequence

> Archived CPU baseline for performance comparisons. Instructions and behavior below apply only to this frozen version. For the current GPU renderer and independent config fields, use the [project README](../../README.md) and [configuration guide](../../CONFIGURATION.md). Do not use this directory as the main application.

This project generates a faceted star, jeweled **K**, particle field, digital-rain portrait reveal and **KARTHIKEYAN** name card. Every output video pixel comes from Python/NumPy/OpenCV/Pillow procedures and the supplied portrait JPEG. Reference video pixels appear only in clearly labelled comparison sheets, never in rendered footage.

The default sequence is 21.8 seconds, 3840 × 2160, 30 fps. The portrait retains the supplied face, glasses, hairstyle, clothing and pose. A feathered silhouette removes the still's outer background. Fixed spatial arrival times and falling particles reveal the image in fragments. The name and opening letter use separately generated font masks.

## Run on Windows

1. Extract the project ZIP to a writable folder. Install 64-bit Python 3.11 or newer with **Add Python to PATH** enabled.
2. Double-click `preview.bat` for a 1280 × 720 preview, or `render.bat` for the 4K master. The first run creates `.venv` and installs the pinned dependencies.
3. FFmpeg is supplied through the imageio-ffmpeg dependency. `setup_tools.py` finds ffprobe on PATH or downloads the Windows essentials build from [Gyan's FFmpeg builds](https://www.gyan.dev/ffmpeg/builds/). A slow/interrupted download can be resumed by running setup again. Internet is needed for first-time setup only.

Manual commands from this folder:

```bat
python -m pip install -r requirements.txt
python setup_tools.py
python main.py --config config.json --frames --tag reviewed --preview
python main.py --config config.json --render
python main.py --config config.json --preset portrait_reveal --preview
python main.py --config config.json --preset portrait_reveal --render
python check_project.py
```

`--preset portrait_reveal` selects the short 271-frame sequence and its matching original audio. The CLI gives this preset distinct output filenames. To make it the default, edit `sequence_preset` and the output paths together in config.json.

## Edit config.json

All asset/output paths are relative to the project folder unless absolute. No source file is overwritten.

| Change | Configuration |
|---|---|
| Opening initial | `opening.letter` (currently K) |
| Name | `titles[0].text` (currently KARTHIKEYAN) |
| Extra credits | Empty `titles[1..3].text` and optional `subtitle`; no invented credits are supplied |
| Font | `typography.font`, `fallback_font`; Windows Georgia Bold is the default |
| Text appearance | `font_height` is a fraction of screen height, `tracking` a fraction of height, `position` normalized x/y; multiline strings use `\n` |
| Text timing | `start`, `end`, `fade_in`, `fade_out` in seconds; hold is the remaining interval |
| Portrait image | `portrait.image`; **also reset `subject_polygon` to null** for a different person/image, or supply a matching grayscale mask via `portrait.mask` |
| Mask for a new image | White means subject, black means background. With neither polygon nor mask, CPU GrabCut attempts foreground extraction. Inspect previews and supply a mask if extraction is inadequate. |
| Portrait framing | `crop`: normalized [left,top,right,bottom]; `anchor`: horizontal silhouette center and top; `height_fraction`; uniform scale always preserves facial proportions |
| Contrast/texture | `black_level`, `brightness`, `contrast`, `gamma`, `stipple_strength`, `line_strength`, `edge_strength` |
| Reveal timing | `portrait.reveal_start/end` relative to the preset's `portrait_offset`; set both preset fade endpoints independently |
| Rain/particles | `rain`, `particles`, `portrait.particle_count`, size, brightness, travel, drift and turbulence |
| Colours | RGB 0–255 under `palette`; deep black is the default background |
| Glow/motion | `effects`; motion blur is restrained two-frame temporal integration, not a physical shutter simulation |
| Audio | `audio.source` or preset default; offset seconds, volume multiplier, fades, codec, bitrate, channels and sample rate |
| Output | `output.path`, dimensions, fps, duration override, CRF, encoder preset and optional bitrate |
| Antialiasing | `supersampling` above 1 renders at larger internal size and downsamples; default 1 renders natively at 4K |

Long titles auto-fit inside the safe width. Font files are not redistributed; if both configured Windows fonts are absent, choose a real `.ttf` path. Text remains editable; it is not baked into the portrait.

Only K and KARTHIKEYAN were specified. The main card stays visible through the later credit slots. Filling a later slot crossfades it over the main name and returns to the main name afterward. Adjust the main card's end time if that return is unwanted. The reference's later credits and blue names are intentionally not copied.

The original audio is included as extracted AAC `.m4a` files. Default gain is 0.65 (about −3.74 dB) because the extended reference's decoded stereo peak exceeded full scale. Its music, timing and stereo channels are preserved; no music is fetched or generated. Set gain to 1 with no filters for AAC stream copy, retaining the source's existing overload. Audio offsets and fades trigger encoding. For new audio, supply enough duration; the renderer never stretches music to fit.

## Files and verification

- `output/KARTHIKEYAN_4K.mp4`: master, with detailed encoded metadata in `qa/`.
- `previews/KARTHIKEYAN_preview.mp4`: lightweight viewing copy.
- `previews/reviewed_contact_sheet.jpg`, `reviewed_comparison.jpg`: timestamp-matched results; left reference/right generated.
- `previews/v1_*`: initial iteration evidence; revised images document changes before master rendering.
- `analysis/scene_breakdown.md` and `.json`: visual stages and observed timing, with explicit uncertainty.
- `analysis/*_every_frame.csv`: metrics for every source frame, not just contact-sheet samples.
- `qa/*validation.json`: actual ffprobe and full-decode checks; `project_checks.json`: behavior checks.
- `qa/final_commands.json`, encode logs and frame metrics: reproducible commands and render evidence.
- `FINAL_REPORT.md`: actual deliverable metadata and limitations after validation.

Reference videos are not needed to rerender and are omitted from the ZIP. To rerun analysis/comparisons, place the two original videos in the sibling `title_card_reference_upload_pack` folder with their original supplied names. Ordinary previews still work without them; comparison generation is skipped. The style PNG is an inspection reference only and is not a renderer dependency.

## Limitations and troubleshooting

The source is a 1600 × 899 already-stylised still. 4K output does not invent missing facial detail, a new pose, depth, or hidden shoulder geometry. Its source digital texture remains part of the subject. The portrait silhouette and brightness distribution therefore differ from the reference person. Gemstones and the star are procedural 2D approximations; the exact original optical effects and trajectories are not recoverable. The source's brief full-screen flash at about 3.73 seconds is softened into the particle transition.

If Python opens the Microsoft Store, install Python from python.org and disable the conflicting execution alias. If the font is missing, edit the font paths. If ffprobe cannot be found, run `python setup_tools.py` or download an essentials ZIP manually and place `ffprobe.exe` in `tools/`; a standard installation's `bin` directory can also be added to PATH. If a process is interrupted, rerun it; only the generated destination is replaced. If memory is tight, reduce output size or supersampling. Rendering is CPU-based and needs no GPU or creative-software subscription. Read terminal errors and QA reports; a video file alone is not proof that validation passed.
