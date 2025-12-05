import os
import random
import math
import pygame
import asyncio
import sys

# Function to create a path for assets
def create_path(relative_path: str) -> str:
    """Create and return the path to the resource depending on whether this is a PyInstaller exe or being run in the development environment."""
    path: str
    if hasattr(sys, '_MEIPASS'):
        path = os.path.join(sys._MEIPASS, relative_path)
    else:
        path = os.path.join(os.path.abspath("."), relative_path)
    return path

# --- Config ---
WIDTH, HEIGHT = 800, 600
FPS = 60
PLAYER_SPEED = 4
PLAYER_MAX_XP = 100
STAR_RECOVER = 20
STAR_INTERVAL_MS = 10000  # every 10 seconds
METEOR_INTERVAL_MS = 10000  # every 10 seconds
ENEMY_BASE_SPAWN_MS = 1200
ENEMY_MIN_SPAWN_MS = 250
ENEMY_SPAWN_DECREASE_PER_SCORE = 6  # spawn faster with score
PLAYER_FIRE_COOLDOWN = 350  # ms
PLAYER_MIN_FIRE_COOLDOWN = 150  # ms minimum cooldown at high score
PLAYER_FIRE_COOLDOWN_DECREASE_PER_SCORE = 1  # ms cooldown decrease per score point
ENEMY_SHOOT_COOLDOWN = (1000, 2200)  # random cooldown for medium/large
ASSET_CHAR_DIR = create_path("asset/character")
ASSET_ENEMY_DIR = create_path("asset/enemy")
PREVIEW_SIZE = (120, 120)  # size used for character preview in selection screen
# per-type enemy image sizes (width, height)
ENEMY_IMAGE_SIZES = {
    'small': (36, 36),
    'medium': (56, 56),
    'large': (80, 80),
}
SOUND_BGM = create_path("asset/audio/bgmusic.mp3")
SOUND_BUTTON = create_path("asset/audio/button.mp3")
SOUND_SHOOT = create_path("asset/audio/shoot.mp3")

COVER_BG = create_path("asset/cover_bg.png")
GAME_BG = create_path("asset/game_bg.png")

# XP values and scores per enemy type
ENEMY_TYPES = {
    "small": {"hp": 1, "score": 1, "can_shoot": False},
    "medium": {"hp": 3, "score": 3, "can_shoot": True, "damage": 1},
    "large": {"hp": 5, "score": 5, "can_shoot": True, "damage": 2},
}

pygame.init()
# initialize mixer explicitly and report status
MIXER_AVAILABLE = True
try:
    pygame.mixer.init()
except Exception as e:
    MIXER_AVAILABLE = False
    print(f"Warning: pygame.mixer could not be initialized: {e}")

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cosmo Clash")
icon = pygame.image.load(create_path("asset/icon.ico"))
pygame.display.set_icon(icon)
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("arial", 26)
BIG_FONT = pygame.font.SysFont("arial", 48, bold=True)
SMALL_FONT = pygame.font.SysFont("arial", 16)

# --- Helpers ---
def load_images_from_folder(folder, fallback_color=(255, 0, 255), size=(48, 48)):
    images = []
    if not os.path.isdir(folder):
        return []
    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        try:
            img = pygame.image.load(create_path(path)).convert_alpha()
            img = pygame.transform.scale(img, size)
            images.append(img)
        except Exception:
            continue
    return images

def load_enemy_images_by_name(folder, per_type_sizes=None):
    mapping = {
        'small': 'enemy1.png',
        'medium': 'enemy2.png',
        'large': 'enemy3.png',
    }
    images = {}
    if not os.path.isdir(folder):
        return images
    for etype, fname in mapping.items():
        path = os.path.join(folder, fname)
        if os.path.isfile(path):
            try:
                img = pygame.image.load(create_path(path)).convert_alpha()
                # scale to per-type size if provided for this etype
                if per_type_sizes and etype in per_type_sizes and per_type_sizes[etype]:
                    img = pygame.transform.scale(img, per_type_sizes[etype])
                images[etype] = img
            except Exception:
                # skip if load/scale fails
                continue
    return images

def draw_text(surf, text, pos, font=FONT, color=(185, 240, 230)):
    surf.blit(font.render(text, True, color), pos)

def clamp(v, a, b):
    return max(a, min(b, v))

# --- UI Elements ---
class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text
    def draw(self, surf):
        pygame.draw.rect(surf, (50,50,50), self.rect, border_radius=8)
        pygame.draw.rect(surf, (200,200,200), self.rect, 3, border_radius=8)
        label = FONT.render(self.text, True, (185, 240, 230))
        lbl_rect = label.get_rect(center=self.rect.center)
        surf.blit(label, lbl_rect)
    def clicked(self, pos):
        return self.rect.collidepoint(pos)

# --- Game Entities ---
class Player(pygame.sprite.Sprite):
    def __init__(self, image=None):
        super().__init__()
        if image:
            self.base_image = image
        else:
            self.base_image = pygame.Surface((48,48), pygame.SRCALPHA)
            pygame.draw.polygon(self.base_image, (0,200,255), [(24,0),(48,48),(0,48)])
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(WIDTH//2, HEIGHT-80))
        self.speed = PLAYER_SPEED
        self.xp = PLAYER_MAX_XP
        self.max_xp = PLAYER_MAX_XP
        self.last_fire = 0
    def update(self, keys):
        vx = vy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            vx = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            vx = self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            vy = -self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            vy = self.speed
        self.rect.x += vx
        self.rect.y += vy
        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
    def draw(self, surf):
        surf.blit(self.image, self.rect)
    def can_fire(self):
        # default uses the global cooldown constant; callers can pass a specific
        # effective cooldown value instead by using the wrapper in Game.
        return pygame.time.get_ticks() - self.last_fire >= PLAYER_FIRE_COOLDOWN
    def can_fire_with(self, cooldown_ms):
        """Check whether the player can fire given a cooldown in ms."""
        return pygame.time.get_ticks() - self.last_fire >= cooldown_ms
    def fire(self):
        self.last_fire = pygame.time.get_ticks()

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, vel, color=(255,255,0), owner="player", damage=1):
        super().__init__()
        self.image = pygame.Surface((6,12), pygame.SRCALPHA)
        pygame.draw.rect(self.image, color, (0,0,6,12))
        self.rect = self.image.get_rect(center=pos)
        self.vel = pygame.Vector2(vel)
        self.owner = owner
        self.damage = damage
    def update(self):
        self.rect.x += int(self.vel.x)
        self.rect.y += int(self.vel.y)
        if self.rect.bottom < 0 or self.rect.top > HEIGHT or self.rect.right < 0 or self.rect.left > WIDTH:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, etype, image=None, speed=1.0):
        super().__init__()
        self.etype = etype
        props = ENEMY_TYPES[etype]
        # keep a base_image for rotation and create visible image
        if image:
            self.base_image = image.copy()
        else:
            size = (40 + (10 if etype=="medium" else 20 if etype=="large" else 0)*2, 30 + (10 if etype=="large" else 0))
            surf = pygame.Surface(size, pygame.SRCALPHA)
            col = (200,80,80) if etype=="small" else (200,160,80) if etype=="medium" else (200,80,200)
            pygame.draw.rect(surf, col, surf.get_rect())
            self.base_image = surf
        # current image (may be rotated)
        self.image = self.base_image.copy()
        # spawn position as float vector to avoid integer truncation stopping movement
        spawn_x = random.randint(20, WIDTH-20)
        spawn_y = -10
        self.rect = self.image.get_rect(midtop=(spawn_x, spawn_y))
        self.pos = pygame.Vector2(self.rect.center)
        self.max_hp = props["hp"]
        self.hp = props["hp"]
        self.score_value = props["score"]
        self.can_shoot = props.get("can_shoot", False)
        self.damage = props.get("damage", 0)
        self.speed = speed * (1.0 + (0.02 * random.random()))  # slight variance
        self.next_shot_time = pygame.time.get_ticks() + random.randint(*ENEMY_SHOOT_COOLDOWN)
    def update(self, player_pos):
        # move toward player position slowly
        dir_vec = pygame.Vector2(player_pos) - self.pos
        if dir_vec.length_squared() > 0.01:
            dir_norm = dir_vec.normalize()
            # move using float position to avoid truncation stopping small movements
            self.pos += dir_norm * self.speed
            # keep the base image (no rotation) and update rect position
            self.image = self.base_image
            self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        # remove if off screen bottom
        if self.rect.top > HEIGHT + 50:
            self.kill()
    def maybe_shoot(self, bullets_group):
        if not self.can_shoot:
            return
        now = pygame.time.get_ticks()
        if now >= self.next_shot_time:
            # shoot toward player's current direction (straight downward or toward center)
            bullets_group.add(Bullet(self.rect.midbottom, (0, 4 + self.damage), color=(255,100,100), owner="enemy", damage=self.damage))
            self.next_shot_time = now + random.randint(*ENEMY_SHOOT_COOLDOWN)

class Star(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # create a five-point star surface with two frames (dim and bright)
        size = 32
        cx = size // 2
        cy = size // 2
        outer_r = size * 0.45
        inner_r = outer_r * 0.45

        def make_star_surface(color, glints=False):
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pts = []
            # 10 points: outer and inner
            for i in range(10):
                angle = math.pi / 2 + i * (2 * math.pi / 10)
                r = outer_r if i % 2 == 0 else inner_r
                x = cx + math.cos(angle) * r
                y = cy - math.sin(angle) * r
                pts.append((int(x), int(y)))
            pygame.draw.polygon(surf, color, pts)

            return surf

        self.dim_image = make_star_surface((255, 210, 60), glints=False)
        self.bright_image = make_star_surface((255, 250, 180), glints=True)
        self.image = self.dim_image
        self.rect = self.image.get_rect(center=(random.randint(20, WIDTH-20), -10))
        self.speed = 1.6
        self.spark_interval = 300  # ms between sparkle frames
        self._last_spark = pygame.time.get_ticks()

    def update(self):
        # sparkle toggle
        now = pygame.time.get_ticks()
        if now - self._last_spark >= self.spark_interval:
            self._last_spark = now
            self.image = self.bright_image if self.image is self.dim_image else self.dim_image

        # move down
        self.rect.y += int(self.speed)
        if self.rect.top > HEIGHT:
            self.kill()


class Meteor(pygame.sprite.Sprite):
    def __init__(self, image=None, pos=(0,0), vel=(0,1)):
        super().__init__()
        if image:
            self.image = image.copy()
        else:
            # fallback: small grey circle
            self.image = pygame.Surface((40,40), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (120,120,120), (20,20), 18)
        self.rect = self.image.get_rect(center=pos)
        self.vel = pygame.Vector2(vel)
    def update(self):
        self.rect.x += int(self.vel.x)
        self.rect.y += int(self.vel.y)
        # kill when fully outside screen bounds
        if (self.rect.top > HEIGHT + 50 or self.rect.bottom < -50 or
            self.rect.left > WIDTH + 50 or self.rect.right < -50):
            self.kill()

# --- Scenes ---
class Game:
    def __init__(self):
        self.state = "start"  # start, select, play, gameover
        # load assets
        self.char_images = load_images_from_folder(ASSET_CHAR_DIR, size=(56,56))
        # load enemy images: keep list fallback (scaled) and also try loading specific files by name
        # fallback list images are scaled to a default 40x40; per-type images are loaded at their
        # natural size so the enemy size matches the image size.
        self.enemy_images = load_images_from_folder(ASSET_ENEMY_DIR, size=(40,40))
        # load per-type enemy images and scale them according to ENEMY_IMAGE_SIZES
        self.enemy_images_by_type = load_enemy_images_by_name(ASSET_ENEMY_DIR, per_type_sizes=ENEMY_IMAGE_SIZES)
        # load meteor/stone images (stone1.png, stone2.png) if present
        self.meteor_images = []
        for fname in (create_path("asset/enemy/stone1.png"), create_path("asset/enemy/stone2.png")):
            p = fname if os.path.isfile(fname) else os.path.join('asset', fname)
            if os.path.isfile(p):
                try:
                    img = pygame.image.load(p).convert_alpha()
                    # scale moderately so stones are visible but not huge
                    img = pygame.transform.scale(img, (48,48))
                    self.meteor_images.append(img)
                except Exception:
                    continue
        # --- Sounds ---
        # try loading bgmusic/button/shoot from project root or asset folder
        def _find_sound_file(name):
            if os.path.isfile(name):
                return name
            alt = os.path.join('asset', name)
            if os.path.isfile(alt):
                return alt
            return None

        # background music (looped)
        bg_path = _find_sound_file(SOUND_BGM)
        if MIXER_AVAILABLE:
            try:
                if bg_path:
                    pygame.mixer.music.load(bg_path)
                    pygame.mixer.music.set_volume(0.5)
                    pygame.mixer.music.play(-1)
                else:
                    print(f"Info: background music file not found: {SOUND_BGM}")
            except Exception as e:
                print(f"Error loading/playing background music '{bg_path}': {e}")
        else:
            print("Info: mixer not available; skipping background music.")

        # button and shoot sounds
        self.snd_button = None
        self.snd_shoot = None
        btn_path = _find_sound_file(SOUND_BUTTON)
        sht_path = _find_sound_file(SOUND_SHOOT)
        if MIXER_AVAILABLE:
            try:
                if btn_path:
                    self.snd_button = pygame.mixer.Sound(btn_path)
                    self.snd_button.set_volume(0.7)
                else:
                    print(f"Info: button sound file not found: {SOUND_BUTTON}")
            except Exception as e:
                self.snd_button = None
                print(f"Error loading button sound '{btn_path}': {e}")
            try:
                if sht_path:
                    self.snd_shoot = pygame.mixer.Sound(sht_path)
                    self.snd_shoot.set_volume(0.6)
                else:
                    print(f"Info: shoot sound file not found: {SOUND_SHOOT}")
            except Exception as e:
                self.snd_shoot = None
                print(f"Error loading shoot sound '{sht_path}': {e}")
        else:
            self.snd_button = None
            self.snd_shoot = None
            print("Info: mixer not available; skipping SFX loading.")
        # --- Background images ---
        self.bg_cover = None
        self.bg_game = None
        def _find_image(name):
            if os.path.isfile(name):
                return name
            alt = os.path.join('asset', name)
            if os.path.isfile(alt):
                return alt
            return None

        # try loading cover/background images and scale to screen size
        try:
            cover_path = COVER_BG if os.path.isfile(COVER_BG) else _find_image(COVER_BG)
            if cover_path:
                img = pygame.image.load(cover_path)
                self.bg_cover = pygame.transform.scale(img, (WIDTH, HEIGHT)).convert()
            else:
                print(f"Info: cover background not found: {COVER_BG}")
        except Exception as e:
            print(f"Error loading cover background '{cover_path}': {e}")
        try:
            game_path = GAME_BG if os.path.isfile(GAME_BG) else _find_image(GAME_BG)
            if game_path:
                img = pygame.image.load(game_path)
                self.bg_game = pygame.transform.scale(img, (WIDTH, HEIGHT)).convert()
            else:
                print(f"Info: game background not found: {GAME_BG}")
        except Exception as e:
            print(f"Error loading game background '{game_path}': {e}")
        # UI
        self.play_btn = Button((WIDTH//2-70, HEIGHT//2+80, 140, 50), "Play")
        self.confirm_btn = Button((WIDTH-240, HEIGHT-130, 150, 45), "Confirm")
        self.playagain_btn = Button((WIDTH//2-80, HEIGHT//2+80, 160, 50), "Play Again")
        # selection
        self.selected_char_index = 0
        # game runtime
        self.reset_game()

    def reset_game(self):
        self.player = Player(self.char_images[self.selected_char_index] if self.char_images else None)
        self.bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.meteors = pygame.sprite.Group()
        self.stars = pygame.sprite.Group()
        self.score = 0
        self.enemy_spawn_timer = pygame.time.get_ticks()
        self.star_timer = pygame.time.get_ticks()
        self.meteor_timer = pygame.time.get_ticks()
        self.last_enemy_spawn_ms = ENEMY_BASE_SPAWN_MS
        self.game_over_time = None

    # Scene: Start
    def draw_start(self, surf):
        if getattr(self, 'bg_cover', None):
            surf.blit(self.bg_cover, (0,0))
        else:
            surf.fill((8,8,20))
        # dark overlay behind header/instructions for readability
        overlay = pygame.Surface((WIDTH-120, 480), pygame.SRCALPHA)
        rect = overlay.get_rect()
        pygame.draw.rect(overlay, (0, 0, 0, 180), rect, border_radius=25)
        surf.blit(overlay, (60, 60))
        draw_text(surf, "Cosmo Clash", (WIDTH//2 - 140, 80), font=BIG_FONT)
        inst = [
            "Game Instructions: ",
            " ",
            "- Use arrow keys / WASD to move. ",
            "- Press Enter key to shoot bullets. ",
            "- The more enemies you kill, the higher your score. "
        ]
        for i, s in enumerate(inst):
            draw_text(surf, s, (WIDTH//2 - 280, 180 + i*30), font=FONT)
        self.play_btn.draw(surf)

    # Scene: Character selection
    def draw_select(self, surf):
        if getattr(self, 'bg_cover', None):
            surf.blit(self.bg_cover, (0,0))
        else:
            surf.fill((10,10,30))
        # dark overlay behind header/instructions for readability
        overlay = pygame.Surface((WIDTH-120, 480), pygame.SRCALPHA)
        rect = overlay.get_rect()
        pygame.draw.rect(overlay, (0, 0, 0, 180), rect, border_radius=25)
        surf.blit(overlay, (60, 60))
        draw_text(surf, "Select Your Character", (WIDTH//2-200, 80), font=BIG_FONT)
        # show single centered character and instructions to preview
        y = 200
        center_x = WIDTH // 2
        if not self.char_images:
            draw_text(surf, "No character images found in folder 'character'. Using default.", (60, y))
            # show one default at center
            default = Player(None).base_image
            scaled = pygame.transform.scale(default, PREVIEW_SIZE)
            r = scaled.get_rect(center=(center_x, y+80))
            surf.blit(scaled, r)
        else:
            img = self.char_images[self.selected_char_index]
            scaled = pygame.transform.scale(img, PREVIEW_SIZE)
            r = scaled.get_rect(center=(center_x, y+80))
            surf.blit(scaled, r)
            draw_text(surf, f"{self.selected_char_index+1} / {len(self.char_images)}", (center_x-20, y+200))
            draw_text(surf, "Use LEFT/RIGHT (or A/D) to preview", (80, HEIGHT-140))
            draw_text(surf, "Click Confirm to play", (80, HEIGHT-110))
        self.confirm_btn.draw(surf)

    # Scene: Play
    def draw_play(self, surf):
        if getattr(self, 'bg_game', None):
            surf.blit(self.bg_game, (0,0))
        else:
            surf.fill((5, 5, 20))
        # stars background
        for _ in range(30):
            pass
        # draw sprites
        for s in self.stars:
            surf.blit(s.image, s.rect)
        for m in getattr(self, 'meteors', []):
            surf.blit(m.image, m.rect)
        for e in self.enemies:
            surf.blit(e.image, e.rect)
        for b in self.bullets:
            surf.blit(b.image, b.rect)
        for b in self.enemy_bullets:
            surf.blit(b.image, b.rect)
        self.player.draw(surf)
        # HUD XP bar
        bar_rect = pygame.Rect(20, 10, WIDTH-200, 18)
        pygame.draw.rect(surf, (60,60,60), bar_rect)
        xp_ratio = self.player.xp / self.player.max_xp
        inner = pygame.Rect(bar_rect.left, bar_rect.top, int(bar_rect.width * xp_ratio), bar_rect.height)
        pygame.draw.rect(surf, (185,240,230), inner)
        pygame.draw.rect(surf, (200,200,200), bar_rect, 2)
        draw_text(surf, f"XP: {self.player.xp}/{self.player.max_xp}", (WIDTH-160, 10))
        draw_text(surf, f"Score: {self.score}", (20, 36))
        draw_text(surf, f"Enemies: {len(self.enemies)}", (180, 36))

    # Scene: Game Over
    def draw_gameover(self, surf):
        if getattr(self, 'bg_cover', None):
            surf.blit(self.bg_cover, (0,0))
        else:
            surf.fill((15,5,5))
        # dark overlay behind header/instructions for readability
        overlay = pygame.Surface((WIDTH-120, 480), pygame.SRCALPHA)
        rect = overlay.get_rect()
        pygame.draw.rect(overlay, (0, 0, 0, 180), rect, border_radius=25)
        surf.blit(overlay, (60, 60))
        draw_text(surf, "Game Over", (WIDTH//2 - 120, 160), font=BIG_FONT)
        draw_text(surf, f"Score: {self.score}", (WIDTH//2 - 60, 240))
        self.playagain_btn.draw(surf)

    # Spawning logic
    def spawn_enemy(self):
        # determine possible types by score thresholds
        choices = []
        if self.score >= 60:
            choices = ["small", "medium", "large"]
        elif self.score >= 20:
            choices = ["small", "medium"]
        else:
            choices = ["small"]
        etype = random.choice(choices)
        # speed increases with score
        speed = 0.6 + 0.5 * (1 + self.score / 40.0)
        # pick an image corresponding to enemy type if available (enemy1.png->small etc.)
        img = None
        if getattr(self, 'enemy_images_by_type', None) and self.enemy_images_by_type.get(etype):
            img = self.enemy_images_by_type.get(etype)
        elif self.enemy_images:
            # fallback: random enemy image
            img = random.choice(self.enemy_images)
        enemy = Enemy(etype, image=img, speed=speed)
        # place randomly at top
        enemy.rect.midtop = (random.randint(20, WIDTH-20), -random.randint(10, 80))
        self.enemies.add(enemy)

    def spawn_meteor(self):
        # spawn a meteor from a random edge, aiming roughly across the screen
        edge = random.choice(['top', 'bottom', 'left', 'right'])
        speed = random.uniform(2.0, 4.0)
        cx, cy = WIDTH/2, HEIGHT/2
        if edge == 'top':
            x = random.randint(0, WIDTH)
            y = -20
            # direction toward somewhere in lower half
            target_x = random.randint(0, WIDTH)
            target_y = random.randint(HEIGHT//2, HEIGHT)
        elif edge == 'bottom':
            x = random.randint(0, WIDTH)
            y = HEIGHT + 20
            target_x = random.randint(0, WIDTH)
            target_y = random.randint(0, HEIGHT//2)
        elif edge == 'left':
            x = -20
            y = random.randint(0, HEIGHT)
            target_x = random.randint(WIDTH//2, WIDTH)
            target_y = random.randint(0, HEIGHT)
        else:  # right
            x = WIDTH + 20
            y = random.randint(0, HEIGHT)
            target_x = random.randint(0, WIDTH//2)
            target_y = random.randint(0, HEIGHT)

        dir_vec = pygame.Vector2(target_x - x, target_y - y)
        if dir_vec.length_squared() == 0:
            dir_vec = pygame.Vector2(0, 1)
        else:
            dir_vec = dir_vec.normalize()
        vel = (dir_vec.x * speed, dir_vec.y * speed)

        img = None
        if getattr(self, 'meteor_images', None):
            img = random.choice(self.meteor_images)
        meteor = Meteor(image=img, pos=(x,y), vel=vel)
        self.meteors.add(meteor)

    def spawn_star(self):
        self.stars.add(Star())

    # Main update per frame
    def update_play(self, events):
        keys = pygame.key.get_pressed()
        self.player.update(keys)

        # Fire player bullet while Enter is held (continuous firing with cooldown).
        # Cooldown decreases as score increases, clamped to a minimum value.
        if keys[pygame.K_RETURN]:
            effective_cd = clamp(PLAYER_FIRE_COOLDOWN - self.score * PLAYER_FIRE_COOLDOWN_DECREASE_PER_SCORE,
                                 PLAYER_MIN_FIRE_COOLDOWN, PLAYER_FIRE_COOLDOWN)
            if self.player.can_fire_with(effective_cd):
                bullet = Bullet(self.player.rect.midtop, (0, -8), color=(180,255,100), owner="player", damage=1)
                self.bullets.add(bullet)
                self.player.fire()
                # play shooting sound
                if getattr(self, 'snd_shoot', None):
                    try:
                        self.snd_shoot.play()
                    except Exception:
                        print("Warning: failed to play shoot sound")

        # Timed spawns: enemy spawn frequency decreases (faster) as score increases
        now = pygame.time.get_ticks()
        spawn_interval = clamp(ENEMY_BASE_SPAWN_MS - self.score * ENEMY_SPAWN_DECREASE_PER_SCORE, ENEMY_MIN_SPAWN_MS, ENEMY_BASE_SPAWN_MS)
        if now - self.enemy_spawn_timer >= spawn_interval:
            self.spawn_enemy()
            self.enemy_spawn_timer = now

        # Star spawn
        if now - self.star_timer >= STAR_INTERVAL_MS:
            self.spawn_star()
            self.star_timer = now

        # Meteor spawn
        if now - self.meteor_timer >= METEOR_INTERVAL_MS:
            self.spawn_meteor()
            self.meteor_timer = now

        # Update groups
        self.bullets.update()
        self.enemy_bullets.update()
        for e in list(self.enemies):
            e.update(self.player.rect.center)
            e.maybe_shoot(self.enemy_bullets)
        self.stars.update()
        # update meteors
        if getattr(self, 'meteors', None):
            self.meteors.update()

        # Collisions: player bullets hitting enemies
        collisions = pygame.sprite.groupcollide(self.bullets, self.enemies, True, False)
        for bullet, enemies in collisions.items():
            for enemy in enemies:
                enemy.hp -= bullet.damage
                if enemy.hp <= 0:
                    self.score += enemy.score_value
                    enemy.kill()
        for b in list(self.enemy_bullets):
            if b.rect.colliderect(self.player.rect):
                self.player.xp -= b.damage
                b.kill()
                if self.player.xp <= 0:
                    self.player.xp = 0
                    self.state = "gameover"
                    self.game_over_time = pygame.time.get_ticks()
                    return

        # enemies colliding with player (touch) -> damage maybe equal to enemy damage or 1
        for enemy in pygame.sprite.spritecollide(self.player, self.enemies, False):
            # collision causes damage equal to enemy damage if they can shoot, else 1
            dmg = enemy.damage if enemy.can_shoot else 1
            enemy.kill()
            self.player.xp -= dmg
            if self.player.xp <= 0:
                self.player.xp = 0
                self.state = "gameover"
                self.game_over_time = pygame.time.get_ticks()
                return

        # player picks up stars
        for star in pygame.sprite.spritecollide(self.player, self.stars, True):
            self.player.xp = clamp(self.player.xp + STAR_RECOVER, 0, self.player.max_xp)

        # player hit by meteors -> -2 XP per hit
        if getattr(self, 'meteors', None):
            for meteor in pygame.sprite.spritecollide(self.player, self.meteors, True):
                self.player.xp -= 2
                if self.player.xp <= 0:
                    self.player.xp = 0
                    self.state = "gameover"
                    self.game_over_time = pygame.time.get_ticks()
                    return

    # Event handling for start/select/gameover clicks
    def handle_event(self, ev):
        # global quit handling
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if self.state == "start":
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.play_btn.clicked(ev.pos):
                    # play click sound
                    if getattr(self, 'snd_button', None):
                        try:
                            self.snd_button.play()
                        except Exception:
                            print("Warning: failed to play button sound")
                    self.state = "select"

        elif self.state == "select":
            # confirm play with mouse
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.confirm_btn.clicked(ev.pos):
                    if getattr(self, 'snd_button', None):
                        try:
                            self.snd_button.play()
                        except Exception:
                            print("Warning: failed to play button sound")
                    self.reset_game()
                    self.state = "play"
            # allow keyboard preview cycling
            if ev.type == pygame.KEYDOWN and self.char_images:
                if ev.key in (pygame.K_LEFT, pygame.K_a):
                    self.selected_char_index = (self.selected_char_index - 1) % len(self.char_images)
                elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selected_char_index = (self.selected_char_index + 1) % len(self.char_images)

        elif self.state == "gameover":
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.playagain_btn.clicked(ev.pos):
                    if getattr(self, 'snd_button', None):
                        try:
                            self.snd_button.play()
                        except Exception:
                            print("Warning: failed to play button sound")
                    self.reset_game()
                    self.state = "play"

    def run_frame(self, events):
        # process input events
        for ev in events:
            self.handle_event(ev)

        # update/draw based on state
        if self.state == "start":
            self.draw_start(screen)
        elif self.state == "select":
            self.draw_select(screen)
        elif self.state == "play":
            self.update_play(events)
            self.draw_play(screen)
        elif self.state == "gameover":
            self.draw_gameover(screen)

async def main():
    game = Game()
    # Async loop: yield to the event loop regularly so pygbag/pyodide can run
    while True:
        events = pygame.event.get()
        game.run_frame(events)
        pygame.display.flip()
        # yield to browser/event loop and limit FPS approximately
        await asyncio.sleep(1.0 / FPS)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        # If async run fails for any reason, fall back to the original synchronous loop
        print(f"Async runtime failed ({e}), falling back to sync loop.")
        game = Game()
        while True:
            events = pygame.event.get()
            game.run_frame(events)
            pygame.display.flip()
            clock.tick(FPS)