#!/usr/bin/env python3
"""
Connect Four Game with Colorful Terminal Display
"""

import os
import sys

# ANSI color codes for a vibrant color scheme
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
GREEN = '\033[92m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
WHITE = '\033[97m'
RESET = '\033[0m'
BOLD = '\033[1m'

class ConnectFour:
    def __init__(self):
        self.board = [[' ' for _ in range(7)] for _ in range(6)]
        self.current_player = 'R'  # R for Red, Y for Yellow
        self.game_over = False
        self.winner = None
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_board(self):
        self.clear_screen()
        print(f"\n{CYAN}{BOLD}🎮 CONNECT FOUR 🎮{RESET}\n")
        
        # Column numbers
        print(f"{MAGENTA}", end="")
        for i in range(7):
            print(f"  {i+1} ", end="")
        print(f"{RESET}")
        
        # Board with borders
        print(f"{BLUE}┌{'─' * 27}┐{RESET}")
        
        for row in self.board:
            print(f"{BLUE}│{RESET}", end="")
            for cell in row:
                if cell == 'R':
                    print(f" {RED}●{RESET} ", end="")
                elif cell == 'Y':
                    print(f" {YELLOW}●{RESET} ", end="")
                else:
                    print(f" {WHITE}○{RESET} ", end="")
                print(f"{BLUE}│{RESET}", end="")
            print()
        
        print(f"{BLUE}└{'─' * 27}┘{RESET}")
        
        # Current player indicator
        if not self.game_over:
            player_color = RED if self.current_player == 'R' else YELLOW
            player_name = "Red" if self.current_player == 'R' else "Yellow"
            print(f"\n{GREEN}Current Player: {player_color}{player_name} ●{RESET}")
    
    def drop_piece(self, column):
        if column < 0 or column >= 7:
            return False
        
        # Find the lowest empty row in the column
        for row in range(5, -1, -1):
            if self.board[row][column] == ' ':
                self.board[row][column] = self.current_player
                return True
        
        return False
    
    def check_winner(self):
        # Check horizontal
        for row in range(6):
            for col in range(4):
                if (self.board[row][col] != ' ' and
                    self.board[row][col] == self.board[row][col+1] ==
                    self.board[row][col+2] == self.board[row][col+3]):
                    return self.board[row][col]
        
        # Check vertical
        for row in range(3):
            for col in range(7):
                if (self.board[row][col] != ' ' and
                    self.board[row][col] == self.board[row+1][col] ==
                    self.board[row+2][col] == self.board[row+3][col]):
                    return self.board[row][col]
        
        # Check diagonal (top-left to bottom-right)
        for row in range(3):
            for col in range(4):
                if (self.board[row][col] != ' ' and
                    self.board[row][col] == self.board[row+1][col+1] ==
                    self.board[row+2][col+2] == self.board[row+3][col+3]):
                    return self.board[row][col]
        
        # Check diagonal (bottom-left to top-right)
        for row in range(3, 6):
            for col in range(4):
                if (self.board[row][col] != ' ' and
                    self.board[row][col] == self.board[row-1][col+1] ==
                    self.board[row-2][col+2] == self.board[row-3][col+3]):
                    return self.board[row][col]
        
        return None
    
    def is_board_full(self):
        return all(self.board[0][col] != ' ' for col in range(7))
    
    def switch_player(self):
        self.current_player = 'Y' if self.current_player == 'R' else 'R'
    
    def play(self):
        while not self.game_over:
            self.display_board()
            
            # Get player input
            try:
                column = int(input(f"\n{CYAN}Enter column (1-7) or 0 to quit: {RESET}")) - 1
                
                if column == -1:
                    print(f"\n{MAGENTA}Thanks for playing!{RESET}")
                    break
                
                if column < 0 or column >= 7:
                    print(f"{RED}Invalid column! Please choose 1-7.{RESET}")
                    input("Press Enter to continue...")
                    continue
                
                if not self.drop_piece(column):
                    print(f"{RED}Column is full! Choose another.{RESET}")
                    input("Press Enter to continue...")
                    continue
                
                # Check for winner
                winner = self.check_winner()
                if winner:
                    self.game_over = True
                    self.winner = winner
                    self.display_board()
                    winner_color = RED if winner == 'R' else YELLOW
                    winner_name = "Red" if winner == 'R' else "Yellow"
                    print(f"\n{GREEN}{BOLD}🎉 {winner_color}{winner_name}{GREEN} WINS! 🎉{RESET}")
                    break
                
                # Check for draw
                if self.is_board_full():
                    self.game_over = True
                    self.display_board()
                    print(f"\n{MAGENTA}{BOLD}It's a DRAW!{RESET}")
                    break
                
                self.switch_player()
                
            except ValueError:
                print(f"{RED}Please enter a valid number!{RESET}")
                input("Press Enter to continue...")
            except KeyboardInterrupt:
                print(f"\n\n{MAGENTA}Game interrupted. Thanks for playing!{RESET}")
                break

def main():
    while True:
        game = ConnectFour()
        game.play()
        
        play_again = input(f"\n{CYAN}Play again? (y/n): {RESET}").lower()
        if play_again != 'y':
            print(f"{MAGENTA}Thanks for playing Connect Four!{RESET}")
            break

if __name__ == "__main__":
    main()