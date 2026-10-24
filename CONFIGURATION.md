# Configuration guide

Edit the existing `config.json` and retain its complete structure. Preview and final render read this file directly. No other settings file overrides it.

## Portrait and opening letter

Set `portrait.image` to the source, for example `assets/my portrait.png` or `D:/Pictures/my portrait.jpeg`. Relative asset paths resolve from the project folder. JSON backslashes must be doubled, so forward slashes are easier.

When changing the image, set `portrait.mask` and `portrait.subject_polygon` to `null` unless you have matching replacements. Priority is explicit mask, explicit polygon, usable source alpha, then automatic foreground extraction. An old mask/polygon otherwise continues to apply.

A custom grayscale mask must match the source dimensions: white retains the subject, black removes the background. Set `portrait.mask` to its path explicitly. A `.mask.png` placed beside the image is not loaded automatically.

| Field | Meaning |
|---|---|
| `portrait.crop` | Normalized `[left, top, right, bottom]`; `[0, 0, 1, 1]` uses the full image. |
| `portrait.fit` | Keep `contain` to preserve proportions. |
| `portrait.anchor` | Normalized horizontal center and top position. |
| `portrait.height_fraction` | Apparent height relative to the frame. |
| `portrait.brightness`, `contrast`, `black_level`, `gamma` | Portrait luminance treatment. |
| `portrait.stipple_strength`, `line_strength`, `edge_strength` | Digital texture and contours. |
| `opening.letter` | Independent opening character, for example `K`. |
| `opening.letter_start`, `letter_end`, `fade_in`, `fade_out` | Opening-letter timing in seconds. |

Changing the letter does not change the portrait or any title.

## Independent title cards

Edit each object in `titles[]` separately. `titles[0].text` is the main name; later objects are separate cards and can all contain different text. To disable a card, set its `text` and `subtitle` to empty strings.

| Field inside a title | Meaning |
|---|---|
| `text` | Main text for that card. |
| `subtitle` | Optional second line. |
| `start`, `end` | Sequence times in seconds; end must follow start. |
| `fade_in`, `fade_out` | Positive transition durations in seconds. |
| `font_height`, `subtitle_height` | Text height relative to frame height. |
| `position` | Normalized `[x, y]` position. |
| `tracking` | Letter spacing relative to height. |

For example, changing `titles[1].text` to `EDITOR` leaves all other cards unchanged. Long titles auto-fit the safe width. Use `\n` within a JSON string for a line break.

When a nonempty later card overlaps the main card, the main title fades away as the first later card enters and remains suppressed for the rest of its interval. It does not return between subsequent cards. Keep later-card times in the intended order and adjust each fade to control the transition.

Set `typography.font` and `typography.fallback_font` to existing font files; fonts are not bundled. Global typography controls tracking and safe area. `palette` supplies RGB colours from 0 to 255.

## Sequence, effects and audio

`sequence_preset` accepts `extended_credits` or `portrait_reveal`. The extended preset lasts 21.8 seconds; the short preset is 271 frames at 30 fps. The CLI `--preset portrait_reveal` adds a filename suffix. Editing `sequence_preset` directly does not add that suffix, so also choose suitable output paths.

Portrait reveal times are relative to `presets.<selected preset>.portrait_offset`. Preset portrait-fade times and title-card times are sequence times. `rain`, `particles`, `portrait.particle_count` and `effects` control density, travel, glow and motion. Keep existing timings to preserve the reference-based sequence.

| Audio field | Meaning |
|---|---|
| `audio.enabled` | `false` generates a silent video. |
| `audio.source` | Custom audio path, or `null` for the selected preset's audio. |
| `audio.offset` | Input audio offset in seconds. |
| `audio.volume` | Gain multiplier; default `0.65`. |
| `audio.fade_in`, `audio.fade_out` | Fade durations in seconds. |

Supply audio long enough for the sequence; it is not stretched to fit. Keep AAC, 44100 Hz and two channels with the current validator, which explicitly checks that format.

## Output and verification

| Field | Meaning |
|---|---|
| `output.path` | Final MP4 path. |
| `output.preview_path` | Preview MP4 path. |
| `output.width`, `height`, `fps` | Final dimensions and frame rate; H.264 dimensions must be even. |
| `output.preview_width` | Preview width; height follows the final aspect ratio. |
| `output.duration` | `null` uses the preset duration; a number overrides it. |
| `output.supersampling` | Internal render scale before downsampling; larger values need more memory/work. |
| `output.crf`, `preview_crf` | Quality targets mapped to the selected encoder's controls. |
| `qa.timestamps` | Extended-sequence preview sample times; keep them inside the video duration. |

Prefer final files in `output/` and preview files in `previews/`. Keep preview artifacts inside the configured preview folder so cleanup can check containment. Text changes never rename output files. Runtime detection selects the actual encoder; see the README for GPU behavior.

After edits, run `preview.bat` and inspect the opening, reveal, every title transition and final fade. The current preview frames/contact sheet come from the encoded preview. Run `render.bat` when satisfied and check `qa/final_run.json` and the output's validation report. Older included QA files describe their recorded renders; they do not validate a newly edited configuration.
