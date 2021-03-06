#!/usr/bin/env pypy
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
from itertools import count
from collections import Counter, OrderedDict, namedtuple
import re
import datetime

# The table size is the maximum number of elements in the transposition table.
TABLE_SIZE = 1e6

# This constant controls how much time we spend on looking for optimal moves.
NODES_SEARCHED = 1e4

# Mate value must be greater than 8*queen + 2*(rook+knight+bishop)z1
# King value is set to twice this value such that if the opponent is
# 8 queens up, but we got the king, we still exceed MATE_VALUE.
MATE_VALUE = 9000

# Our board is represented as a 120 character string. The padding allows for
# fast detection of moves that don't stay within the board.
A1, H1, A8, H8 = 91, 98, 21, 28
initial = (
    '         \n'  #   0 -  9
    '         \n'  #  10 - 19
    ' rnbqkbnr\n'  #  20 - 29
    ' pppppppp\n'  #  30 - 39
    ' ........\n'  #  40 - 49
    ' ........\n'  #  50 - 59
    ' ........\n'  #  60 - 69
    ' ........\n'  #  70 - 79
    ' PPPPPPPP\n'  #  80 - 89
    ' RNBQKBNR\n'  #  90 - 99
    '         \n'  # 100 -109
    '          '   # 110 -119
)


initial2 = (
    '         \n'  #   0 -  9
    '         \n'  #  10 - 19
    ' .......K\n'  #  20 - 29
    ' ........\n'  #  30 - 39
    ' k.P.....\n'  #  40 - 49
    ' .......p\n'  #  50 - 59
    ' ........\n'  #  60 - 69
    ' ........\n'  #  70 - 79
    ' ........\n'  #  80 - 89
    ' ........\n'  #  90 - 99
    '         \n'  # 100 -109
    '          '   # 110 -119
)

###############################################################################
# Move and evaluation tables
###############################################################################

N, E, S, W = -10, 1, 10, -1
directions = {
    'P': (N, 2*N, N+W, N+E),
    'N': (2*N+E, N+2*E, S+2*E, 2*S+E, 2*S+W, S+2*W, N+2*W, 2*N+W),
    'B': (N+E, S+E, S+W, N+W),
    'R': (N, E, S, W),
    'Q': (N, E, S, W, N+E, S+E, S+W, N+W),
    'K': (N, E, S, W, N+E, S+E, S+W, N+W)
}

pst = {
    'P': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 198, 198, 198, 198, 198, 198, 198, 198, 0,
        0, 178, 198, 198, 198, 198, 198, 198, 178, 0,
        0, 178, 198, 198, 198, 198, 198, 198, 178, 0,
        0, 178, 198, 208, 218, 218, 208, 198, 178, 0,
        0, 178, 198, 218, 238, 238, 218, 198, 178, 0,
        0, 178, 198, 208, 218, 218, 208, 198, 178, 0,
        0, 178, 198, 198, 198, 198, 198, 198, 178, 0,
        0, 198, 198, 198, 198, 198, 198, 198, 198, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'B': (
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 797, 824, 817, 808, 808, 817, 824, 797, 0,
        0, 814, 841, 834, 825, 825, 834, 841, 814, 0,
        0, 818, 845, 838, 829, 829, 838, 845, 818, 0,
        0, 824, 851, 844, 835, 835, 844, 851, 824, 0,
        0, 827, 854, 847, 838, 838, 847, 854, 827, 0,
        0, 826, 853, 846, 837, 837, 846, 853, 826, 0,
        0, 817, 844, 837, 828, 828, 837, 844, 817, 0,
        0, 792, 819, 812, 803, 803, 812, 819, 792, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'N': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 627, 762, 786, 798, 798, 786, 762, 627, 0,
        0, 763, 798, 822, 834, 834, 822, 798, 763, 0,
        0, 817, 852, 876, 888, 888, 876, 852, 817, 0,
        0, 797, 832, 856, 868, 868, 856, 832, 797, 0,
        0, 799, 834, 858, 870, 870, 858, 834, 799, 0,
        0, 758, 793, 817, 829, 829, 817, 793, 758, 0,
        0, 739, 774, 798, 810, 810, 798, 774, 739, 0,
        0, 683, 718, 742, 754, 754, 742, 718, 683, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'R': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 1258, 1263, 1268, 1272, 1272, 1268, 1263, 1258, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'Q': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 2529, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'K': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 60098, 60132, 60073, 60025, 60025, 60073, 60132, 60098, 0,
        0, 60119, 60153, 60094, 60046, 60046, 60094, 60153, 60119, 0,
        0, 60146, 60180, 60121, 60073, 60073, 60121, 60180, 60146, 0,
        0, 60173, 60207, 60148, 60100, 60100, 60148, 60207, 60173, 0,
        0, 60196, 60230, 60171, 60123, 60123, 60171, 60230, 60196, 0,
        0, 60224, 60258, 60199, 60151, 60151, 60199, 60258, 60224, 0,
        0, 60287, 60321, 60262, 60214, 60214, 60262, 60321, 60287, 0,
        0, 60298, 60332, 60273, 60225, 60225, 60273, 60332, 60298, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
}


weights = {'Mobility': 10,
               'P': 100,
               'N': 320,
               'B': 330,
               'R': 500,
               'Q': 900,
               'K': 20000
               }

###############################################################################
# Chess logic
###############################################################################

class Position(namedtuple('Position', 'board score wc bc ep kp turn')):
    """ A state of a chess game
    board -- a 120 char representation of the board
    score -- the board evaluation
    wc -- the castling rights
    bc -- the opponent castling rights
    ep - the en passant square
    kp - the king passant square
    """

    def genMoves(self):
        # For each of our pieces, iterate through each possible 'ray' of moves,
        # as defined in the 'directions' map. The rays are broken e.g. by
        # captures or immediately in case of pieces such as knights.
        for i, p in enumerate(self.board):
            if not p.isupper():
                continue
            for d in directions[p]:
                for j in count(i+d, d):
                    q = self.board[j]
                    # Stay inside the board
                    if self.board[j].isspace():
                        break
                    # Castling
                    if (i == A1 or i == A8) and q == 'K' and self.wc[0]:
                        yield (j, j-2)
                    if (i == H1 or i == H8) and q == 'K' and self.wc[1]:
                        yield (j, j+2)
                    # No friendly captures
                    if q.isupper():
                        break
                    # special king stuff: no suicidal
                    if p == 'K' and self.board[j+N] in ['q', 'k', 'r']:
                        break
                    if p == 'K' and self.board[j+S] in ['q', 'k', 'r']:
                        break
                    if p == 'K' and self.board[j+E] in ['q', 'k', 'r']:
                        break
                    if p == 'K' and self.board[j+W] in ['q', 'k', 'r']:
                        break
                    if p == 'K' and self.board[j+W+N] in ['q', 'k', 'b', 'p']:
                        break
                    if p == 'K' and self.board[j+E+N] in ['q', 'k', 'b', 'p']:
                        break
                    if p == 'K' and self.board[j+E+S] in ['q', 'k', 'b']:
                        break
                    if p == 'K' and self.board[j+W+S] in ['q', 'k', 'b']:
                        break
                    # this is not considering to be in the line of a queen, bishop or rook, or in the range of a knight
                    # Special pawn stuff
                    if p == 'P' and d in (N+W, N+E) and q == '.' and j not in (self.ep, self.kp):
                        break
                    if p == 'P' and d in (N, 2*N) and q != '.':
                        break
                    if p == 'P' and d == 2*N and (i < A1+N or self.board[i+N] != '.'):
                        break
                    # Move it
                    yield (i, j)
                    # Stop crawlers from sliding
                    if p in ('P', 'N', 'K'):
                        break
                    # No sliding after captures
                    if q.islower():
                        break

    def rotate(self):
        turn = self.turn
        if turn == 'white':
            turn = 'black'
        else:
            turn = 'white'
        return Position(
            self.board[::-1].swapcase(), -self.score,
            self.bc, self.wc, 119-self.ep, 119-self.kp, turn)

    def move(self, move):
        i, j = move
        p, q = self.board[i], self.board[j]
        put = lambda board, i, p: board[:i] + p + board[i+1:]
        # Copy variables and reset ep and kp
        board = self.board
        wc, bc, ep, kp = self.wc, self.bc, 0, 0
        # score = self.score + self.value(move)
        # Actual move
        board = put(board, j, board[i])
        board = put(board, i, '.')
        score = self.evaluate()
        # Castling rights
        if i == A1:
            wc = (False, wc[1])
        if i == H1:
            wc = (wc[0], False)
        if j == A8:
            bc = (bc[0], False)
        if j == H8:
            bc = (False, bc[1])
        # Castling
        if p == 'K':
            wc = (False, False)
            if abs(j-i) == 2:
                kp = (i+j)//2
                board = put(board, A1 if j < i else H1, '.')
                board = put(board, kp, 'R')
        # Special pawn stuff
        if p == 'P':
            if A8 <= j <= H8:
                board = put(board, j, 'Q')
            if j - i == 2*N:
                ep = i + N
            if j - i in (N+W, N+E) and q == '.':
                board = put(board, j+S, '.')
        # We rotate the returned position, so it's ready for the next player
        return Position(board, score, wc, bc, ep, kp, self.turn).rotate()

    def value(self, move):
        i, j = move
        p, q = self.board[i], self.board[j]
        # Actual move
        score = pst[p][j] - pst[p][i]
        # Capture
        if q.islower():
            score += pst[q.upper()][j]
        # Castling check detection
        if abs(j-self.kp) < 2:
            score += pst['K'][j]
        # Castling
        if p == 'K' and abs(i-j) == 2:
            score += pst['R'][(i+j)//2]
            score -= pst['R'][A1 if j < i else H1]
        # Special pawn stuff
        if p == 'P':
            if A8 <= j <= H8:
                score += pst['Q'][j] - pst['P'][j]
            if j == self.ep:
                score += pst['P'][j+S]
        return score

    def evaluate(self):
        white_pieces_string = re.sub(r'[^PNRBQK]', '', self.board)
        black_pieces_string = re.sub(r'[^pnrbqk]', '', self.board).upper()
        pawn_difference = abs(len(re.sub(r'[^P]', '', white_pieces_string)) - len(re.sub(r'[^P]', '', black_pieces_string)))
        bishop_difference = abs(len(re.sub(r'[^B]', '', white_pieces_string)) - len(re.sub(r'[^B]', '', black_pieces_string)))
        knight_difference = abs(len(re.sub(r'[^N]', '', white_pieces_string)) - len(re.sub(r'[^N]', '', black_pieces_string)))
        rook_difference = abs(len(re.sub(r'[^R]', '', white_pieces_string)) - len(re.sub(r'[^R]', '', black_pieces_string)))
        queen_difference = abs(len(re.sub(r'[^Q]', '', white_pieces_string)) - len(re.sub(r'[^Q]', '', black_pieces_string)))
        king_difference = abs(len(re.sub(r'[^K]', '', white_pieces_string)) - len(re.sub(r'[^K]', '', black_pieces_string)))
        material_score = weights['K']*king_difference + \
                         weights['Q']*queen_difference + \
                         weights['R']*rook_difference + \
                         weights['N']*knight_difference + \
                         weights['B']*bishop_difference + \
                         weights['P']*pawn_difference

        player1_mobility = 0
        for move in self.genMoves():
            player1_mobility += 1
        self.rotate()
        player2_mobility = 0
        for move in self.genMoves():
            player2_mobility += 1
        self.rotate()
        mobility_score = weights['Mobility']*(abs(player1_mobility - player2_mobility))
        if self.turn == 'white':
            turn_value = 1
        else:
            turn_value = -1
        return (material_score + mobility_score) * turn_value


Entry = namedtuple('Entry', 'depth score move')
tp = OrderedDict()


###############################################################################
# Search logic
###############################################################################

nodes = 0


###################
# Minmax with Alpha Beta cut offs
###################
def alphabeta(position, depth, alpha, beta):
    """Returns a tuple (score, bestmove) for the position at the given depth"""
    # if depth > 0:
    #    nullscore = -alphabeta(position.rotate(), alpha, beta, depth-3)
    # else:
    #    nullscore = position.score
    if depth == 0:
        return position.score
    if len(re.sub(r'[^Kk]', '', position.board)) < 2:
        return position.score*8
    entry = tp.get(position)
    if entry is not None and entry.depth >= depth and (
            entry.score < beta or entry.score >= alpha):
        return entry.score
    else:
        if position.turn == "white":
            bestmove = None
            for move in sorted(position.genMoves(), key=position.value, reverse=True):
                if depth <= 0 and position.move(move).score < 150:
                    break
                score = alphabeta(position.move(move), depth - 1, alpha, beta)
                if score > alpha:  # white maximizes his score
                    alpha = score
                    bestmove = move
                    if alpha >= beta:  # alpha-beta cutoff
                        break
            tp[position] = Entry(depth, alpha, bestmove)
            if len(tp) > TABLE_SIZE:
                tp.popitem()
            #if bestmove:
            #    print("\t" * depth, "LEAF: %s%s" % (render(bestmove[0]), render(bestmove[1])))
            return alpha
        else:
            bestmove = None
            for move in sorted(position.genMoves(), key=position.value, reverse=True):
                score = alphabeta(position.move(move), depth - 1, alpha, beta)
                if score < beta:  # black minimizes his score
                    beta = score
                    bestmove = move
                    if alpha >= beta:  # alpha-beta cutoff
                        break
            tp[position] = Entry(depth, alpha, bestmove)
            if len(tp) > TABLE_SIZE:
                tp.popitem()
            #if bestmove:
            #    print("\t" * depth, "LEAF: %s%s" % (render(119-bestmove[0]), render(119-bestmove[1])))
            return beta

###############################################################################
# User interface
###############################################################################


def render(i):
    rank, fil = divmod(i - A1, 10)
    return chr(fil + ord('a')) + str(-rank + 1)


def main():
    pos = Position(initial2, 0, (False, False), (False, False), 0, 0, 'white')
    # pos = Position(initial, 0, (True, True), (True, True), 0, 0, 'white')

    print(' '.join(pos.board))
    print("%s turn" % pos.turn)
    while True:
        # We add some spaces to the board before we print it.
        # That makes it more readable and pleasing.
        # Fire up the engine to look for a move.
        move = None
        start = datetime.datetime.now()
        score = alphabeta(pos, 10, -3*MATE_VALUE, 3*MATE_VALUE)
        entry = tp.get(pos)
        if entry is not None:
            move = entry.move
        current_turn = pos.turn
        pos = pos.move(move)
        if current_turn == "black":
            print("%s move:" % current_turn, render(119-move[0]) + render(119-move[1]))
            print(' '.join(pos.board))
        else:
            print("%s move:" % current_turn, render(move[0]) + render(move[1]))
            print(' '.join(pos.rotate().board))

        if len(re.sub(r'[^Kk]', '', pos.board)) < 2:
            if score <= -MATE_VALUE:
                print("Black won")
            if score >= MATE_VALUE:
                print("White won")
            break
        current_turn = pos.turn
        print("Elapsed time: %s" % (datetime.datetime.now()-start))
        print("%s turn" % current_turn)


if __name__ == '__main__':
    main()
