# Cadenza

A local experimental AI classical composer. Generate eight fresh candidates, select one, listen with recorded instruments, and export MIDI or M4A. No API key or account is required to compose.

![Cadenza icon](dist/assets/icon-192.png)

[Open the browser app](https://bugbytedev.github.io/Cadenza/) · [Download desktop source and macOS app](https://github.com/BugByteDev/Cadenza/releases/latest)

## Desktop: macOS, Windows and Linux

Install Python 3.11+ with Tk, Node.js 22+ and FFmpeg (including ffplay) on your PATH. The trained models, bundled JavaScript engine and recorded instrument banks are included; npm is only needed to rebuild browser dependencies.

- **Windows:** install Python from python.org with Tk and PATH enabled, Node.js from nodejs.org, and FFmpeg with ffplay. Double-click `Launch-Cadenza.bat`.
- **macOS:** `brew install python python-tk node ffmpeg`, then run `python3 desktop.py`. The included app bundle uses installed runtimes.
- **Ubuntu/Debian:** install `python3 python3-tk nodejs ffmpeg` through your package manager (Node must be 22+), then run `./launch-cadenza.sh`.

Other desktop distributions can run the same Python and Node sources after installing those dependencies. The native interface has been exercised on macOS. Automated model-generation, Python syntax and SoundFont rendering checks passed on Windows, Linux and macOS in GitHub Actions. These checks do not replace native GUI testing on Windows and Linux.

The interface reflows and scrolls in small windows. Generated MIDI, note JSON and M4A are saved automatically to your library: `%LOCALAPPDATA%/Cadenza/generated` on Windows, `~/Library/Application Support/Cadenza/generated` on macOS, and `$XDG_DATA_HOME/Cadenza/generated` (or `~/.local/share/Cadenza/generated`) on Linux. Save buttons copy files to your chosen location. No premade songs are shipped as app generation resources.

## Phones, tablets and browsers

The responsive browser app runs local neural inference and recorded instrument rendering in workers. Serve `dist/` over HTTPS, or run `python3 serve.py` locally. For a static deployment, run `npm ci --ignore-scripts` and `npm run build:web` to copy sound banks into the browser build. On phones and tablets, use the hosted URL; localhost on your computer is not a public URL.

MIDI export and WAV audio rendering work without a backend. M4A export uses the local desktop/server FFmpeg encoder. Standalone browser builds offer WAV rather than claiming AAC encoding support on every browser. Add to Home Screen where supported. Assets used during online sessions are cached for offline use; sound banks must be loaded once. Browser history stores the latest 30 pieces locally; download MIDI for permanent storage.

## Models and training

The main music model has 201,700 parameters, two 384-unit tanh hidden layers and eight events of context. Six output heads predict pitch, onset gap, duration, velocity, harmony root and chord quality. A separate 182,922-parameter word model generates titles. Learned inference is combined with musical-form rules, accompaniment rules and heuristic selection; this is not a concert-level long-context composer or a trained aesthetic judge.

The general model was fine-tuned on 1,870 MIDI performances/parts, with 220 validation and 249 test files, from MAESTRO v3 plus composer-exclusive public-domain Mutopia supplements. The additional archive contains 2,666 unique MIDI files from 1,110 editions credited to 227 composers; parts and movements are not counted as full works. Six instrument models were trained from scratch with composer-disjoint splits: violin, cello, flute, strings, clarinet and bassoon. Harp uses the general model because independent labelled data was insufficient. String evaluation covers few composers. Lower event loss does not establish better music.

Reports, dataset fingerprints and per-edition provenance are included. Read [MODEL_CARD.md](MODEL_CARD.md) for limitations. MIDI fragment screening reduces exact short-fragment reuse; it does not guarantee that melodies never resemble existing music.

## Sounds and licenses

- Code: MIT, see `LICENSE`.
- Main music weights: supplied under CC BY-NC-SA 4.0 for noncommercial experimentation; MAESTRO is provided under that license. See `MODEL_LICENSE.md`.
- MAESTRO: [official source](https://magenta.tensorflow.org/datasets/maestro); Hawthorne et al., *Enabling Factorized Piano Music Modeling and Generation with the MAESTRO Dataset*, ICLR 2019.
- Mutopia: public-domain editions with retained per-edition provenance. Dickinson title-training source: [Project Gutenberg](https://www.gutenberg.org/ebooks/12242).
- Piano: recorded Yamaha C5 by Alexander Holm, CC BY 3.0. One sampled velocity layer, minor-third sample spacing, direct non-looping playback with natural decay. Converted to mono PCM, limited to eight seconds with boundary fade.
- Other instruments: GeneralUser GS by S. Christian Collins, complete license in `sounds/`. Portable rendering uses SpessaSynth Core (Apache-2.0); archive decoder fflate (MIT). Dependency licenses are retained in `dist/vendor/`.

## Development

`npm ci --ignore-scripts`, `npm run build:web`, `node verify.mjs`, and `python3 portable_smoke.py`. Source rebuild uses NumPy: `python3 collect_repertoire.py`, `python3 train.py --epochs 30 --hidden 384 --init dist/general-initial.json`, then `python3 train_titles.py`. Training downloads the MAESTRO MIDI archive into RAM and needs several GB of RAM. Python inference is orchestrated by the native UI; the learned JS inference and SoundFont engine use Node.

GitHub Actions includes a desktop compatibility matrix and a manually triggered Pages deployment. The source release contains no authentication files, generated personal library, bundled Python/Node runtime or signed installer.
