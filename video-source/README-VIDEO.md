# Editing the birthday video

The video is generated from `content.json` (all the text) plus `render_video.py` (layout, timing, effects).
The soundtrack is `soundtrack.m4a`. You never edit the MP4 directly.

## 1. Change the text
Open `content.json` in any text editor (VS Code, Notepad, TextEdit). Only change the text between the quotes.
- Keep lists as lists: `"s2b": ["line one", "line two"]` means two lines on screen.
- Emoji are fine. Keep the quotes and commas.
- `s1_num` is the big 13. Changing it changes the number everywhere in scene 1.
- Keep lines short. Long lines are wrapped automatically, but very long text can run off the screen or be hard to read.

Preview a frame without a full render:

    python render_video.py stills previews 5.0 13.0 30.0

Then open the PNGs in the `previews` folder.

## 2. Build the full video
You need Python 3.10+ and FFmpeg installed (ffmpeg must be on your PATH).

    pip install numpy opencv-python pillow scipy

From inside `video-source`:

    python render_video.py

This writes `../assets/video/birthday-video.mp4`, replacing the old one. A full build takes several minutes; a fast PC is quicker.

## Timing
Scene timings are fixed in `render_video.py` (scene 1 at 0 s, goat at 4 s, birthday at 10 s, personal at 18 s, school at 28 s, finale at 38 s, end at 48 s). If you make a line much longer, it may need more time on screen. Tell the assistant and it can adjust the timing for you.

## Changing photos
Swap the files in `../assets/photos/` but keep the same names, or tell the assistant what to change.
