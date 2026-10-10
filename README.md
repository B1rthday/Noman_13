# Chapter 13 — The Birthday Mission

A small interactive birthday mission (website) plus a cinematic 48-second vertical video premiere.
Everything is local. No backend, no accounts, no analytics, no third-party requests.

## Run locally

Open the folder in VS Code and use Live Server, or run from this folder:

    python3 -m http.server 8000

Then open http://localhost:8000. Opening index.html directly also works for most browsers, but a local server is more reliable for the video.

## What's in the site

1. Transmission intro with "Begin the mission"
2. Mission 001: the goat evidence reveal, freeze-frame, and reaction
3. Mission 002: a charge-to-unlock emblem ("LEVEL 13 UNLOCKED")
4. Mission 003: a photo gallery with lightbox (tap, arrow keys, or swipe) and a hidden note
5. Mission 004: five Chapter 13 wish tiles, revealed one by one
6. The Birthday Premiere: the video player, then a final message and "Replay the birthday mission"

The website is intentionally different from the video. It does not repeat the video's captions.

## Files

- index.html, styles.css, script.js: the site
- assets/video/birthday-video.mp4: the 48 s vertical video (1080x1920, 30 fps, H.264 + AAC, about 12 MB)
- assets/audio/ambient-loop.mp3: a short original ambient loop for the optional Music button
- assets/audio/original-instrumental.mp3: the soundtrack from the previous version (unused by the new site)
- assets/photos/: the three original photos, unchanged
- assets/fonts/: subset Lora fonts (SIL Open Font License), so the site doesn't need Google Fonts
- assets/images/video-poster.jpg: poster frame for the video player
- _previous_version/: the old site and video, kept for reference

## Sound

Music is off by default and starts only after the visitor taps the Music button. It pauses while the video plays and resumes when the video ends. The video's own audio is the main soundtrack.

## Hosting

Free static hosts work well: Netlify Drop (drag the folder), Cloudflare Pages, or GitHub Pages. The total size is about 14 MB.

Privacy: photos and video are public to anyone with the URL on a public host. For a private surprise, send the folder directly, or use a private or password-protected host.

## Editing the video text

The video is generated from `video-source/content.json`. Edit the text there, then rebuild with `python render_video.py` inside `video-source/`. See `video-source/README-VIDEO.md`.

## Reduced motion and accessibility

Respects prefers-reduced-motion (no shake, no burst particles, no zoom). Keyboard navigable, visible focus rings, meaningful alt text, and 44 px minimum tap targets.
