from typing import Callable
from card import *
import random


class _GameState(Enum):
    INITIALIZED = 1
    READY_TO_START = 2
    STARTED = 3
    ONGOING = 4
    FINISHED = 5
    DESTROYED = 6  # not sure if we need it


class _Player:
    discord_tag: str
    nickname: str

    def __init__(self, discord_tag, nickname):
        self.discord_tag = discord_tag
        self.nickname = nickname


class Game:
    state: _GameState
    players: list[_Player] = []
    playersToCards: dict[_Player, list[Card]] = {}
    deck: list[Card]
    current_card: Card
    current_color: Color
    admin: _Player
    currentPlayer: _Player
    pickup_stack = 0
    max_card_id = -1
    is_reversed = 1  # -1 if reversed

    on_ready_callbacks: list[Callable[[], None]] = []
    on_started_callbacks: list[Callable[[], None]] = []
    on_ongoing_callbacks: list[Callable[[], None]] = []
    on_finished_callbacks: list[Callable[[], None]] = []
    on_destroyed_callbacks: list[Callable[[], None]] = []

    def process_turn(self, discord_tag: str, card_id: int | None, color: Color | None):
        player = next(player for player in self.players if player.discord_tag == discord_tag)
        if card_id is None:
            self.pick_up_cards(player, 1 + self.pickup_stack)
            self.pickup_stack = 0
            return
        cards = self.playersToCards[player]
        card = next(card for card in cards if card.id == card_id)
        p = 1
        # todo: add a check for compatibility
        if card is Reverse:
            self.is_reversed *= -1
        elif card is Skip:
            p += 1
        elif card is Plus:
            self.pickup_stack += 2
        elif card is WildPlus:
            self.pickup_stack += 4

        # todo: implement pickup logic
        # todo:
        self.currentPlayer = self.players[
            (self.players.index(self.currentPlayer) + 2 * self.is_reversed) % len(self.players)]

    def pick_up_cards(self, player: _Player, count: int):
        for i in range(count):
            if len(self.deck) == 0:
                self.refill_deck()
            self.playersToCards[player].append(self.deck.pop())

    def refill_deck(self):
        for i in range(10):
            self.deck += self.create_number_cards(i)
            if i != 0:
                self.deck += self.create_number_cards(i)
        self.create_plus_cards()
        self.create_wild_cards()
        self.create_reverse_cards()
        self.create_skip_cards()
        random.shuffle(self.deck)

    def create_reverse_cards(self):
        for color in range(1, 5):
            for i in range(2):
                self.max_card_id += 1
                self.deck.append(Reverse(Color(color), self.max_card_id))

    def create_skip_cards(self):
        for color in range(1, 5):
            for i in range(2):
                self.max_card_id += 1
                self.deck.append(Skip(Color(color), self.max_card_id))

    def create_plus_cards(self):
        for color in range(1, 5):
            for j in range(2):
                self.max_card_id += 1
                self.deck.append(Plus(Color(color), self.max_card_id))

    def create_wild_cards(self):
        for i in range(4):
            self.max_card_id += 1
            self.deck.append(WildPlus(self.max_card_id))
            self.max_card_id += 1
            self.deck.append(Wild(self.max_card_id))

    def create_number_cards(self, number: int) -> list[Card]:
        r = Number(Color.RED, number, self.max_card_id + 1)
        b = Number(Color.GREEN, number, self.max_card_id + 2)
        g = Number(Color.GREEN, number, self.max_card_id + 3)
        y = Number(Color.YELLOW, number, self.max_card_id + 4)
        self.max_card_id += 4
        return [r, b, g, y]

    def __init__(self, admin):
        self.state = _GameState.INITIALIZED
        self.__admin__ = admin
        self.players.append(admin)

    def add_player(self, player: _Player):
        if self.state != _GameState.READY_TO_START:
            return
        else:
            self.players.append(player)

    def on_ready(self):
        if self.state == _GameState.READY_TO_START:
            for callback in self.on_ready_callbacks:
                callback()

    def on_started(self):
        if self.state == _GameState.STARTED:
            for callback in self.on_started_callbacks:
                callback()

    def on_ongoing(self):
        if self.state == _GameState.ONGOING:
            for callback in self.on_ongoing_callbacks:
                callback()

    def on_finished(self):
        if self.state == _GameState.FINISHED:
            for callback in self.on_finished_callbacks:
                callback()

    def on_destroyed(self):
        if self.state == _GameState.DESTROYED:
            for callback in self.on_destroyed_callbacks:
                callback()
