# FirstPlay

**Let AI play your game like a real first-time player.**

Pixels in. Keyboard and mouse out. No game hooks, semantic trees, test IDs, or debug APIs.

FirstPlay launches a Windows game, finds its real window, shows screenshots to a vision model, lets the model take one human-like action at a time, and writes down where a first-time player gets confused.

> **Status:** v0.1 bootstrap. The core Windows → screenshot → vision → input → report loop is implemented. Expect sharp edges while the public test corpus grows.

## Why FirstPlay?

Automated tests are great at proving that code works. They are much worse at answering questions like:

- Can a new player find the Play button?
- Is movement discoverable without reading the source code?
- Does the result screen make the next action obvious?
- Is important information visually legible?
- Does the game ever leave a player staring at the screen with no idea what to do?

FirstPlay deliberately knows **less** than your test suite. It sees the game through pixels and acts through ordinary mouse and keyboard input.

```text
$ firstplay run ./build/MyGame.exe --goal "Start a run and play for 60 seconds"

FirstPlay 0.1
Game window: MyGame  1280x720
Model: gpt-5.6-luna

[00:03] sees      Main menu with a large PLAY button
[00:04] action    click (642, 511)
[00:09] sees      Character in a room; no movement hint visible
[00:10] friction  MEDIUM — movement is not explained
[00:11] action    hold 'w' for 0.5s
[00:15] sees      Character moved upward; WASD discovered
...

Report written to firstplay-runs/20260905-221500/
```

A run produces:

```text
firstplay-runs/20260905-221500/
├── report.md
├── timeline.json
└── screenshots/
    ├── 000.png
    ├── 001.png
    └── ...
```

## Quick start

Requirements:

- Windows 10/11
- Python 3.11+
- A game executable you are allowed to test
- An OpenAI API key for the v0.1 vision adapter

```powershell
git clone https://github.com/madowaku/firstplay.git
cd firstplay
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

$env:OPENAI_API_KEY="..."

firstplay doctor

firstplay run "C:\Games\MyGame\MyGame.exe" `
  --goal "Start the game and try to understand how to play" `
  --seconds 60
```

The default model is `gpt-5.6-luna`. Override it with `--model` or `FIRSTPLAY_MODEL`.

## What the model is allowed to do

v0.1 intentionally exposes a tiny action vocabulary:

- `click(x, y)`
- `key(key)`
- `hold_key(key, seconds)` — capped at 2 seconds per action
- `type_text(text)`
- `wait(seconds)`
- `stop(reason)`

The model receives only the current game screenshot, the test goal, and a short history of its own visible observations/actions. It does **not** receive your scene tree, source code, DOM, accessibility tree, internal game state, or telemetry.

## Privacy and safety

FirstPlay crops screenshots to the launched game's top-level window when Windows can resolve it. If the window cannot be found, the run stops rather than silently uploading the whole desktop.

Screenshots are sent to the configured model provider. Do not test builds that display secrets, personal information, private chat, credentials, or other content you would not send to that provider.

FirstPlay only automates software you launch explicitly. Keep your hands near the mouse during early runs. PyAutoGUI's fail-safe remains enabled: moving the pointer to the upper-left corner aborts automation.

## Design principles

1. **Black-box by default.** A player does not get your internal state, so FirstPlay should not either.
2. **One observation, one action.** No invisible macro scripts pretending to be a playtest.
3. **Evidence over vibes.** Every finding links back to a screenshot and timeline step.
4. **Engine-agnostic.** Godot, Unity, GameMaker, custom engines: pixels are pixels.
5. **Useful before clever.** A 60-second first-run friction report beats a giant autonomous QA fantasy.

## CLI

```text
firstplay doctor
firstplay run GAME.exe [OPTIONS]

Options:
  --goal TEXT          What the first-time player should try to accomplish.
  --model TEXT         Vision model. Default: FIRSTPLAY_MODEL or gpt-5.6-luna.
  --seconds INTEGER    Maximum run duration. Default: 60.
  --max-steps INTEGER  Maximum model actions. Default: 30.
  --launch-wait FLOAT  Seconds to wait after launching the game. Default: 2.0.
  --output PATH        Parent directory for run artifacts. Default: firstplay-runs.
  --close-game         Terminate the launched process after the run.
```

## Roadmap

### v0.1 — The loop

- [x] Launch a Windows executable
- [x] Resolve and focus the game's real window
- [x] Capture only that window
- [x] Handle Windows DPI scaling for screenshot/input alignment
- [x] Vision-model observation + one-action decision
- [x] Mouse click, key press, and short key-hold execution
- [x] Screenshot evidence
- [x] JSON timeline + Markdown friction report
- [x] CLI doctor command
- [ ] Validate against several Godot and Unity builds
- [ ] Add a tiny public demo game + README GIF

### v0.2 — Better playtesting

- [ ] Detect repeated/stuck states
- [ ] Session-level summary pass
- [ ] GIF / contact-sheet evidence
- [ ] Configurable player personas without revealing hidden state
- [ ] Better gamepad support

### Later

- [ ] macOS / Linux adapters
- [ ] Additional vision providers
- [ ] Browser-game adapter
- [ ] CI-friendly replay mode
- [ ] Optional human review UI

## Non-goals

FirstPlay is not a replacement for unit tests, integration tests, deterministic bot tests, accessibility testing, or engine-aware debugging. It is the awkward new player you wish you could summon before every release.

## Development

```powershell
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT © 2026 madowaku
