import json
import time

import chess
import chess.pgn
import chess.engine
import os

from bots.bots import *
from tourney.elo import calculate_elos
from tourney.game_result import GameResult
from tourney.player import Player


class TourneyManager:
  # default constructor
  def __init__(self, match_length: int):
    # Tourney settings
    self.match_length = match_length
    self.elo_k = 32 # controls Elo gain/loss

    self.game_results: list[GameResult] = []
    self.players: list[Player] = []

    self.game_number = 0 # increment after a game result is assigend this. pseudo id

  # Play a single game between players
  def play_game(self, wp: Player, bp: Player, turn_limit: int) -> GameResult:
    board = chess.Board()
    game = chess.pgn.Game()
    node = game
    turns = 0

    start_time = time.time()
    while not board.is_game_over() and turns <= turn_limit:
      move = None
      if board.turn:
        move, comment = wp.move(board)
      else:
        move, comment = bp.move(board)
      node = node.add_variation(move)
      if comment != '': # empty comments mean no comment (!)
        node.comment = comment
      board.push(move)
      turns += 1
    game.end()
    game_result = GameResult()
    game_result.from_chess(wp, bp, board, game)

    # set ID. setting it externally here cuz its tourney_level, even if its stored on GR level.
    game_result.game_number = self.game_number
    self.game_number += 1

    game_result.time = time.time() - start_time
    return game_result
  
  def update_player_data(self, wp: Player, bp: Player, gr: GameResult):
    # Updates player ELO, wins, losses, draws after result

    d = 0 # default
    if gr.winning_color == 'white':
      d = 1 # for elo calc
      wp.wins += 1
      bp.losses += 1
    elif gr.winning_color == 'black':
      d = 0 # for elo calc
      wp.losses += 1
      bp.wins += 1
    else: # draw case
      d = 0.5
      bp.draws += 1
      wp.draws += 1 

    wp.elo, bp.elo = calculate_elos(wp.elo, bp.elo, self.elo_k, d)
    print(str(wp) + ': ' + str(wp.elo) + ', ' + str(bp) + ': ' + str(bp.elo))
  

  # Helper to play multiple games between two bots
  def play_match(self, p1: Player, p2: Player, count, swap_colors=False) -> list[GameResult]:
    print('=========<' + str(p1) + ' [vs] ' + str(p2) + '>=========')

    # Time and play games
    start_time = time.time()
    grs = []  # game results array

    for i in range(count):
      print('Game [' + str(i + 1) + '/' + str(count) + "] of [" + str(p1) + "] vs [" + str(p2) + "]")
      gr = self.play_game(p1, p2, 300)
      print(gr.winning_player + ' wins in [' + str(gr.moves) + '] turns in [' + str(gr.time) + '] seconds')
      self.update_player_data(p1, p2, gr)
      grs.append(gr)

    if swap_colors:  # TODO: Recursive case, could be cleaner
      grs2 = self.play_match(p2, p1, count, False)
      grs += grs2

    print('Total Time: ' + str(time.time() - start_time))
    print()

    return grs

  # Play round robin tourney
  # Skips mirror matches
  # Stores game results and player results
  def play_tournament(self, players: list[Player]):
    self.players = players
    # build player ids
    counter = 0
    for player in self.players:
      player.id = counter
      counter += 1

    players = self.players
    match_length = self.match_length

    start_time = time.time()
    match_total = (len(players) ** 2) - len(players)
    match_count = 0
    grs = []
    for p1 in players:
      for p2 in players:
        if str(p1) != str(p2): #skip self play matches
          match_count += 1
          # Play a single one-sided match (no color swapping)
          print('Match ' + str(match_count) + '/' + str(match_total))
          grs += self.play_match(p1, p2, match_length, False)
    total_time = time.time() - start_time
    print('Total time for tournament: ' + str(total_time))
    self.game_results = grs
    return grs
  
  # Adds a single new player to the tourney and runs games with that player
  def continue_tourney(self, new_player: Player):
    match_count = 0
    match_total = len(self.players)
    new_player.id = len(self.players)  # assign new player the appropriate id

    grs = self.game_results
    start_time = time.time()

    # new player as white
    # note the loose convention of match orders being all white then all black plays is brokn here
    for old_player in self.players:
      match_count += 1

      print('Match ' + str(match_count) + '/' + str(match_total))
      # TODO : should validate previous results and new match length are same.
      grs += self.play_match(new_player, old_player, self.match_length, False)
      # Note : playing continued games out of order here.
      grs += self.play_match(old_player, new_player, self.match_length, False)

    total_time = time.time() - start_time

    self.players.append(new_player) # have this at the end, bc we iterate through players above

    print('Total time for continution: ' + str(total_time))
  

  # Exports stored game data as JSON
  def export_game_data(self, file_name) -> str:
    data = []
    for gr in self.game_results:
      data.append(gr.to_dict())

    json_data = json.dumps(data, indent=2)
    # TODO : refactor this into a constant, the export name
    with open(file_name + '_games.json', 'w') as file:
      file.write(json_data,)

    # files.download('output.csv')

  # Exports stored player data as jsonz`z`
  def export_player_data(self, file_name):
    data = []
    for player in self.players:
      data.append(player.to_dict())
      
    json_data = json.dumps(data, indent=2)

    # TODO : refactor this into a constant, the export name
    with open(file_name + '_players.json', 'w') as file:
      file.write(str(json_data),)

  # Generates a labelled dictionary of bots
  # Used for importing tourneys from JSON
  def create_bot_dict(self) -> dict:
    bot_dict = {}

    # Initializing vanilla bots
    bot_ar = AlwaysRandomBot()
    bot_sk = SuicideKingBot()
    bot_pacifist = PacifistBot()
    bot_berserk = BerserkBot()

    stockfish_path = '../../stockfish/stockfish-ubuntu-20.04-x86-64' # TODO : refactor
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, stockfish_path)
    engine = chess.engine.SimpleEngine.popen_uci(filename) # TODO : should close this after continuing tourney
    base_limit = chess.engine.Limit(time=0.1, depth=5)

    bot_sf = Stockfish100Bot(engine, base_limit)
    bot_sf_5 = WaterBot(bot_sf, bot_ar, 0.05)
    bot_sf_10 = WaterBot(bot_sf, bot_ar, 0.1)
    bot_sf_20 = WaterBot(bot_sf, bot_ar, 0.2)
    bot_panic = PanicFishBot(engine, base_limit)

    bot_dict["Random"] = bot_ar
    bot_dict["Suicide King"] = bot_sk
    bot_dict["Pacifist"] = bot_pacifist
    bot_dict["Berserk"] = bot_berserk
    bot_dict["Panicfish"] = bot_panic
    bot_dict["Stockfish 100"] = bot_sf
    bot_dict["Stockfish 5"] = bot_sf_5
    bot_dict["Stockfish 10"] = bot_sf_10
    bot_dict["Stockfish 20"] = bot_sf_20

    # TODO : handle engine return for closing
    return bot_dict


  def import_game_results(self, file_name):
    game_results = []

    # import game results
    # parameter requires file extension.
    path = '../../' + file_name  # TODO : refactor
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, path)
    g_file = open(filename)
    g_jdata = json.loads(g_file.read())
    for game_dict in g_jdata:
      gr = GameResult()
      gr.from_dict(game_dict)
      game_results.append(gr)
    self.game_results = game_results

  
  def import_player_results(self, file_name):
    # Import json file
    # parameter requires file extension.
    path = '../../' + file_name # TODO : refactor
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, path)
    p_file = open(filename)
    p_jdata = json.loads(p_file.read())

    # Convert list of dicts into list of player objects
    players = []
    bot_dict = self.create_bot_dict()
    for player_dict in p_jdata:
      name = player_dict['Name']
      bot = bot_dict[name]
      player = Player(bot, name)
      player.from_dict(player_dict)
      players.append(player)

    self.players = players
