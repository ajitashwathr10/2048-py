import pygame
import random
import sqlite3
import json
import os
from typing import List, Tuple, Dict

class Game:
    def __init__(self):
        pygame.init()
        self.config = self.load_config()
        self.apply_config_settings()
        self.setup_game_environment()
        self.initialize_game_systems()

        self.conn = sqlite3.connect('game_database.db')
        self.create_database_tables()
    
    def load_config(self) -> Dict:
        default_config = {
            'screen_width': 800,
            'screen_height': 900,
            'theme': 'dark',
            'particle_effects': True,
            'sound_volume': 0.5,
            'difficulty': 'medium'
        }
        config_path = 'game_config.json'
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as config_file:
                    user_config = json.load(config_file)
                    return {**default_config, **user_config}
            return default_config
        except json.JSONDecodeError:
            return default_config
    
    def apply_config_settings(self):
        self.width = self.config['screen_width']
        self.height = self.config['screen_height']
        self.screen = pygame.display.set_mode((self.width, self.height))
        
        self.theme = self.config.get('theme')
        self.color_scheme = self.get_color_scheme()
        
        self.particle_effects = self.config['particle_effects']
        self.sound_volume = self.config['sound_volume']
        pygame.mixer.music.set_volume(self.sound_volume)

    def create_database_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS high_scores (
                       id INTEGER PRIMARY KEY,
                       score INTEGER,
                       difficulty TEXT,
                       date DATETIME DEFAULT CURRENT_TIMESTAMP
                       )
                       ''') 
        self.conn.commit()
    
    def load_fonts(self) -> Dict:
        try:
            return {
                'small': pygame.font.Font(None, 24),
                'medium': pygame.font.Font(None, 36),
                'large': pygame.font.Font(None, 48)
            }
        except pygame.error as e:
            print(f"Error loading fonts: {e}")
            return {}
        
    def start_game(self) -> List[List[int]]:
        self.score = 0
        self.game_over = False
        grid_size = self.difficulty_levels[self.current_difficulty]['grid_size']
        self.mat = [[0] * grid_size for _ in range(grid_size)]
        self.spawn_initial_tiles()
        return self.mat

    def add_new_tile(self):
        grid_size = len(self.mat)
        empty_cells = [(r, c) for r in range(grid_size) for c in range(grid_size) if self.mat[r][c] == 0]
        if not empty_cells:
            return False
        r, c = random.choice(empty_cells)
        spawn_prob = self.difficulty_levels[self.current_difficulty]['spawn_probs']
        self.mat[r][c] = 2 if random.random() < float(spawn_prob['2']) else 4
        return True
    
    def create_particle_effect(self, value: int, position: Tuple[int, int]):
        if self.particle_effects:
            self.particles.append({
                'value': value,
                'position': position,
                'lifetime': 30,
                'color': self.color_scheme['tile_colors'].get(value, (200, 200, 200))
            })

    def update_particles(self):
        self.particles = [p for p in self.particles if p['lifetime'] > 0]
        for particle in self.particles:
            particle['lifetime'] -= 1
    
    def render_particles(self):
        for particle in self.particles:
            pos = particle['position']
            alpha = int((particle['lifetime'] / 30) * 255)
            surface = pygame.Surface((50, 50), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*particle['color'], alpha), (25, 25), 25)
            self.screen.blit(surface, (pos[1] * 100 + 25, pos[0] * 100 + 25))

    def init_audio(self):
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"Error initializing audio: {e}")

    def show_notification(self, title: str, description: str, duration: int = 3000):
        self.notification_queue.append({
            'title': title,
            'description': description,
            'start_time': pygame.time.get_ticks(),
            'duration': duration
        })

    def update_notifications(self):
        current_time = pygame.time.get_ticks()
        self.notification_queue = [n for n in self.notification_queue
                                if current_time - n['start_time'] < n['duration']]
    
    def render_notifications(self):
        y_offset = 10
        for notification in self.notification_queue:
            text = self.fonts['medium'].render(
                f"{notification['title']}: {notification['description']}",
                True,
                (255, 255, 255)
            )
            self.screen.blit(text, (10, y_offset))
            y_offset += 40

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(60)
        self.cleanup()

    def get_color_scheme(self):
        color_schemes = {
            'dark': {
                'background': (50, 50, 50),
                'tile_colors': {
                    2: (238, 228, 218),
                    4: (237, 224, 200),
                    8: (242, 177, 121),
                    16: (245, 149, 99)
                }
            },
            'light': {
                'background': (250, 248, 239),
                'tile_colors': {
                    2: (205, 193, 180),
                    4: (232, 217, 196),
                    8: (237, 177, 121),
                    16: (245, 149, 99)
                }
            }
        }
        return color_schemes.get(self.theme, color_schemes['dark'])

    def setup_game_environment(self):
        pygame.display.set_caption('2048')
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.running = True
        self.fonts = self.load_fonts()
        
        self.game_states = {
            'main_menu': True,
            'playing': False,
            'settings': False,
            'high_scores': False,
            'achievements': False
        }

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and self.game_states['playing']:
                self.handle_game_input(event.key)
    
    def handle_gane_input(self, key):
        key_actions = {
            pygame.K_LEFT: lambda: self.move_tiles('left'),
            pygame.K_RIGHT: lambda: self.move_tiles('right'),
            pygame.K_UP: lambda: self.move_tiles('up'),
            pygame.K_DOWN: lambda: self.move_tiles('down')
        }
        if key in key_actions:
            key_actions[key]()

    def update(self):
        self.update_particles()
        self.update_notifications()
        if self.game_states['playing']:
            self.check_game_over()

    def render(self):
        self.screen.fill(self.color_scheme['background'])
        if self.game_states['playing']:
            self.render_game()
        elif self.game_states['main_menu']:
            self.render_menu()
        self.render_particles()
        self.render_notifications()
        pygame.display.flip()
    
    def render_game(self):
        """
        Renders the game board
        """
        pass

    def render_menu(self):
        """
        Renders the main menu
        """
        pass
    def check_game_over(self):
        if not any(0 in row for row in self.mat):
            for i in range(len(self.mat)):
                for j in range(len(self.mat)):
                    if(i < len(self.mat) - 1 and self.mat[i][j] == self.mat[i + 1][j]) or (j < len(self.mat) - 1 and self.mat[i][j] == self.mat[i][j + 1]):
                        return False
            self.game_over = True
            self.save_score()

    def save_score(self):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO high_scores (score, difficulty) VALUES (?, ?)',
            (self.score, self.current_difficulty)
        )
        self.conn.commit()
    
    def cleanup(self):
        if hasattr(self, 'conn'):
            self.conn.close()
        pygame.quit()


    def initialize_game_systems(self):
        self.difficulty_levels = {
            'easy': {'grid_size': 4, 'max_undo': 5, 'spawn_prob': {'2': 0.95, '4': 0.05}},
            'medium': {'grid_size': 4, 'max_undo': 3, 'spawn_prob': {'2': 0.90, '4': 0.10}},
            'hard': {'grid_size': 5, 'max_undo': 2, 'spawn_prob': {'2': 0.85, '4': 0.15}}
        }
        self.current_difficulty = 'medium'
        self.mat = self.start_game()
        self.achievements = self.create_achievement_system()
        self.move_history = []
        self.particles = []
        self.init_audio()
        self.notification_queue = []

    #Changes
        self.score = 0
        self.high_score = 0
        self.board_size = 4
        self.grid = [[0] * self.board_size for _ in range(self.board_size)]
        self.game_over = False
        self.spawn_initial_tiles()

    def spawn_initial_tiles(self):
        for _ in range(2):
            self.spawn_new_tile()
    
    def spawn_new_tile(self):
        empty_cells = [(i, j) for i in range(self.board_size)
                       for j in range(self.board_size) if self.grid[i][j] == 0]
        if empty_cells:
            i, j = random.choice(empty_cells)
            self.grid[i][j] = 2 if random.random() < 0.9 else 4
    #Changes

    def create_achievement_system(self):
        return {
            '2048_reached': {'unlocked': False, 'reward': 'Novice Merger', 'description': 'Reach 2048 tile'},
            '4096_reached': {'unlocked': False, 'reward': 'Tile Master', 'description': 'Reach 4096 tile'},
            'no_undo_win': {'unlocked': False, 'reward': 'Pure Skill', 'description': 'Win without using undo'}
        }

    def move_tiles(self, direction):
        grid_size = len(self.mat)
        moved = False
        directions = {
            'left': lambda r, c: (r, c),
            'right': lambda r, c: (r, grid_size - 1 - c),
            'up': lambda r, c: (c, r),
            'down': lambda r, c: (grid_size - 1 - c, r)
        }
        
        def process_direction(directions):
            nonlocal moved
            new_mat = [[0] * grid_size for _ in range(grid_size)]
            
            for r in range(grid_size):
                row = [x for x in self.mat[r] if x != 0]
                merged_row = []
                
                while row:
                    current = row.pop(0)
                    if row and current == row[0]:
                        current *= 2
                        row.pop(0)
                        moved = True
                        self.create_particle_effect(current, (r, len(merged_row)))
                    merged_row.append(current)
                
                merged_row += [0] * (grid_size - len(merged_row))
                new_mat[r] = merged_row
            
            return new_mat
        if direction in directions:
            self.mat = process_direction(directions[direction])

        if moved:
            self.add_new_tile()
            self.check_achievements()

    def render_achievement_notification(self):
        if self.notification_queue:
            achievement = self.notification_queue.pop(0)
            title = achievement['reward']
            description = achievement['description']
            reward = achievement['reward']
            self.show_notification(title, description, reward)
            self.notification_queue.append(achievement)

        for notification in self.notification_queue:
            title = notification['reward']
            description = notification['description']
            reward = notification['reward']
            self.show_notification(title, description, reward)

        if not self.notification_queue: 
            self.game_states['achievements'] = False
        
    def check_achievements(self):
        max_tile = max(max(row) for row in self.mat)
        achievement_checks = [
            (2048, '2048_reached'),
            (4096, '4096_reached')
        ]
        for tile_value, achievement_key in achievement_checks:
            if max_tile >= tile_value and not self.achievements[achievement_key]['unlocked']:
                self.achievements[achievement_key]['unlocked'] = True
                self.notification_queue.append(self.achievements[achievement_key])

    def menu_action_start_game(self):
        self.game_states['main_menu'] = False
        self.game_states['playing'] = True
        self.mat = self.start_game()

    def menu_action_change_difficulty(self):
        difficulties = list(self.difficulty_levels.keys())
        current_index = difficulties.index(self.current_difficulty)
        self.current_difficulty = difficulties[(current_index + 1) % len(difficulties)]

    def menu_action_show_high_scores(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT score, difficulty FROM high_scores ORDER BY score DESC LIMIT 10')
        return cursor.fetchall()
    
    #Changes
    def cleanup(self):
        self.conn.close()
        pygame.quit()

def main():
    game = Game()
    try:
        game.run()
    except Exception as e:
        print(f"Error occurred: {e}")
        game.cleanup()

if __name__ == '__main__':
    main()

