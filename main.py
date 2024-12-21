import pygame
import random
import sqlite3
import json
import os
from typing import Dict, List, Tuple

class Game:
    def __init__(self):
        pygame.init()
        self.load_and_apply_config()
        self.initialize_game_state()
        self.setup_database()

    def load_and_apply_config(self):
        default_config = {
            'screen_width': 800,
            'screen_height': 900,
            'theme': 'dark',
            'particle_effects': True,
            'sound_volume': 0.5,
            'difficulty': 'medium'
        }
        
        try:
            with open('game_config.json', 'r') as f:
                self.config = {**default_config, **json.load(f)}
        except (FileNotFoundError, json.JSONDecodeError):
            self.config = default_config

        # Apply settings
        self.screen = pygame.display.set_mode((self.config['screen_width'], self.config['screen_height']))
        pygame.display.set_caption('2048')
        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.config['sound_volume'])
        
        self.color_scheme = {
            'dark': {
                'background': (50, 50, 50),
                'tile_colors': {2: (238, 228, 218), 4: (237, 224, 200), 
                              8: (242, 177, 121), 16: (245, 149, 99)}
            },
            'light': {
                'background': (250, 248, 239),
                'tile_colors': {2: (205, 193, 180), 4: (232, 217, 196),
                              8: (237, 177, 121), 16: (245, 149, 99)}
            }
        }[self.config['theme']]

    def initialize_game_state(self):
        self.difficulty_settings = {
            'easy': {'size': 4, 'spawn_rates': (0.95, 0.05)},
            'medium': {'size': 4, 'spawn_rates': (0.90, 0.10)},
            'hard': {'size': 5, 'spawn_rates': (0.85, 0.15)}
        }
        
        self.current_difficulty = self.config['difficulty']
        self.board_size = self.difficulty_settings[self.current_difficulty]['size']
        
        # Game state
        self.score = 0
        self.game_over = False
        self.running = True
        self.state = 'main_menu'  # main_menu, playing, settings
        
        # Initialize grid
        self.grid = [[0] * self.board_size for _ in range(self.board_size)]
        self.spawn_initial_tiles()
        
        # Visual elements
        self.particles = []
        self.notifications = []
        self.fonts = {size: pygame.font.Font(None, size) 
                     for size in [24, 36, 48]}
        self.clock = pygame.time.Clock()

    def setup_database(self):
        self.conn = sqlite3.connect('game_database.db')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS high_scores
                           (id INTEGER PRIMARY KEY,
                            score INTEGER,
                            difficulty TEXT,
                            date DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        self.conn.commit()

    def spawn_initial_tiles(self):
        for _ in range(2):
            self.spawn_new_tile()

    def spawn_new_tile(self) -> bool:
        empty_cells = [(r, c) for r in range(self.board_size) 
                      for c in range(self.board_size) if self.grid[r][c] == 0]
        if not empty_cells:
            return False
            
        r, c = random.choice(empty_cells)
        rates = self.difficulty_settings[self.current_difficulty]['spawn_rates']
        self.grid[r][c] = 2 if random.random() < rates[0] else 4
        return True

    def move_tiles(self, direction: str) -> bool:
        original_grid = [row[:] for row in self.grid]
        merged = False
        
        def process_line(line: List[int]) -> List[int]:
            nonzero = [x for x in line if x != 0]
            merged_line = []
            i = 0
            while i < len(nonzero):
                if i + 1 < len(nonzero) and nonzero[i] == nonzero[i + 1]:
                    merged_line.append(nonzero[i] * 2)
                    self.score += nonzero[i] * 2
                    i += 2
                else:
                    merged_line.append(nonzero[i])
                    i += 1
            return merged_line + [0] * (len(line) - len(merged_line))

        if direction in ['left', 'right']:
            for i in range(self.board_size):
                row = self.grid[i]
                if direction == 'right':
                    row = row[::-1]
                self.grid[i] = process_line(row)
                if direction == 'right':
                    self.grid[i] = self.grid[i][::-1]
                    
        elif direction in ['up', 'down']:
            for j in range(self.board_size):
                col = [self.grid[i][j] for i in range(self.board_size)]
                if direction == 'down':
                    col = col[::-1]
                processed = process_line(col)
                if direction == 'down':
                    processed = processed[::-1]
                for i in range(self.board_size):
                    self.grid[i][j] = processed[i]

        merged = any(original_grid[i][j] != self.grid[i][j]
                    for i in range(self.board_size)
                    for j in range(self.board_size))
                    
        if merged:
            self.spawn_new_tile()
            self.check_game_over()
        
        return merged

    def check_game_over(self) -> bool:
        if any(0 in row for row in self.grid):
            return False
            
        for i in range(self.board_size):
            for j in range(self.board_size):
                if (i < self.board_size - 1 and self.grid[i][j] == self.grid[i + 1][j]) or \
                   (j < self.board_size - 1 and self.grid[i][j] == self.grid[i][j + 1]):
                    return False
                    
        self.game_over = True
        self.save_score()
        return True

    def save_score(self):
        self.conn.execute('INSERT INTO high_scores (score, difficulty) VALUES (?, ?)',
                         (self.score, self.current_difficulty))
        self.conn.commit()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(60)
        self.cleanup()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and self.state == 'playing':
                key_actions = {
                    pygame.K_LEFT: 'left',
                    pygame.K_RIGHT: 'right',
                    pygame.K_UP: 'up',
                    pygame.K_DOWN: 'down'
                }
                if event.key in key_actions:
                    self.move_tiles(key_actions[event.key])

    def update(self):
        # Update particles
        self.particles = [p for p in self.particles if p['lifetime'] > 0]
        for p in self.particles:
            p['lifetime'] -= 1
            
        # Update notifications
        current_time = pygame.time.get_ticks()
        self.notifications = [n for n in self.notifications 
                            if current_time - n['start_time'] < n['duration']]

    def render(self):
        self.screen.fill(self.color_scheme['background'])
        
        if self.state == 'playing':
            self.render_grid()
        elif self.state == 'main_menu':
            self.render_menu()
            
        self.render_particles()
        self.render_notifications()
        pygame.display.flip()

    def cleanup(self):
        self.conn.close()
        pygame.quit()

if __name__ == '__main__':
    game = Game()
    try:
        game.run()
    except Exception as e:
        print(f"Error occurred: {e}")
        game.cleanup()
