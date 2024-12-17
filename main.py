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
    
    def load_config(self):
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
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading configuration: {e}")
            print("Falling back to default configuration")
        return default_config
    
    def apply_config_settings(self):
        self.width = self.config.get('screen_width', 800)
        self.height = self.config.get('screen_height', 900)
        self.screen = pygame.display.set_mode((self.width, self.height))
        
        self.theme = self.config.get('theme', 'dark')
        self.color_scheme = self.get_color_scheme()
        
        self.particle_effects = self.config.get('particle_effects', True)
        self.sound_volume = self.config.get('sound_volume', 0.5)

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
    
    def load_fonts(self):
        return {
            'small': pygame.font.Font(None, 24),
            'medium': pygame.font.Font(None, 36),
            'large': pygame.font.Font(None, 48)
        }
    
    def start_game(self):
        grid_size = self.difficulty_levels[self.current_difficulty]['grid_size']
        return [[0] * grid_size for _ in range(grid_size)]

    def add_new_tile(self):
        grid_size = len(self.mat)
        empty_cells = [(r, c) for r in range(grid_size) for c in range(grid_size) if self.mat[r][c] == 0]
        if not empty_cells:
            return False
        r, c = random.choice(empty_cells)
        spawn_prob = self.difficulty_levels[self.current_difficulty]['spawn_probs']
        self.mat[r][c] = 2 if random.random() < float(spawn_prob['2']) else 4
        return True
    
    def create_particle_effect(self, value, position):
        if self.particle_effects:
            self.particles.append({
                'value': value,
                'position': position,
                'lifetime': 30
            })

    def init_audio(self):
        pygame.mixer.init()

    def get_color_scheme(self):
        """Dynamic color schemes based on theme"""
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
        """Comprehensive game environment setup"""
        pygame.display.set_caption('2048')
        self.clock = pygame.time.Clock()
        self.fonts = self.load_fonts()
        
        self.game_states = {
            'main_menu': True,
            'playing': False,
            'settings': False,
            'high_scores': False,
            'achievements': False
        }

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
        
        def process_direction(direction_func):
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
        """Display achievement notifications"""
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

def main():
    game = Game()
    game.run()

if __name__ == '__main__':
    main()
