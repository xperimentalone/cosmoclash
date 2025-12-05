# 🌌 Cosmo Clash

A retro-inspired **2D pixel-style space shooting game** built with Python.  
Blast through waves of enemy ships, dodge meteors, and survive the endless void of space in this fast-paced arcade adventure.

---

## 🎮 Game Description

Cosmo Clash is a classic shoot-'em-up where you pilot a starfighter against relentless cosmic foes.  
With pixel art visuals and immersive sound effects, the game combines nostalgic arcade vibes with modern Python-powered gameplay.

- **Genre:** 2D Space Shooter  
- **Style:** Pixel art, retro arcade  
- **Platform:** Python (Pygame recommended)  
- **Objective:** Survive as long as possible while racking up points by destroying enemy ships and avoiding hazards.

---

## 🕹️ Game Instructions

### Controls
- **Arrow Keys** → Move your ship  
- **Enter Key** → Fire lasers  


### Gameplay
1. Start the game and control your starfighter.  
2. Shoot down enemy ships to earn points.  
3. Collect power-ups to recover your XP.  
4. Survive as long as possible — the longer you last, the tougher the enemies become!  

---

## 📸 Assets & Credits
- Images: Courtesy of NASA (public domain space imagery)
- Sound Effects & Background Music: From Pixabay.com (royalty-free audio)
Special thanks to the open-source community for tools and resources that made this project possible.

---

## 🌐 Web packaging with `pygbag`

This project now includes an async-friendly main loop so it can be packaged to run in the browser using `pygbag` (Pyodide + Emscripten). Below are recommended steps and important notes.

### What changed in `main.py`
- Added `import asyncio`.
- The `main()` loop was converted to `async def main()` and uses `await asyncio.sleep(1.0 / FPS)` so the Pyodide event loop can run. This is required for browser builds with `pygbag`.
- The `__main__` guard calls `asyncio.run(main())` and includes a synchronous fallback loop if the async runner fails.

### Quick local run (Windows PowerShell)
```powershell
python -m pip install -U pygame
python main.py
```

### Build & publish (recommended workflow)
1. Install `pygbag`:

```powershell
python -m pip install -U pygbag
```

2. Verify CLI and build (run from project root where `main.py` lives):

```powershell
pygbag --help
pygbag .
```

3. Serve the build locally (if build output is in `build/`):

```powershell
cd build
python -m http.server 8000
# then open http://localhost:8000
```

4. Publish to GitHub Pages:
- Option A: Push the built files to the `gh-pages` branch.
- Option B: Copy build files to `docs/` and enable GitHub Pages from `main/docs`.

### Important tips
- Include `asset/` files in the build output. Verify images and audio are present after `pygbag .`.
- For better browser audio compatibility, include `ogg`/`wav` fallbacks in `asset/audio/` in addition to `mp3`.
- If the game is unresponsive in the browser, confirm `await asyncio.sleep(...)` is present in the main loop.

If you'd like, I can add a GitHub Actions workflow to automatically build the web package and publish it to `gh-pages`, and/or add `ogg` fallbacks for audio.