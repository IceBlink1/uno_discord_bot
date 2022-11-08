from typing import Callable, Coroutine, Awaitable
from card import *
import random


class GameState(Enum):
    INITIALIZED = 1
    READY_TO_START = 2
    STARTED = 3
    ONGOING = 4
    FINISHED = 5
    DESTROYED = 6  # not sure if we need it


class Player:
    discord_tag: str
    nickname: str

    def __init__(self, discord_tag, nickname):
        self.discord_tag = discord_tag
        self.nickname = nickname


class Game:
    state: GameState
    players: list[Player] = []
    playersToCards: dict[Player, list[Card]] = {}
    deck: list[Card] = []
    current_card: Card
    current_color: Color
    admin: Player
    current_player: Player
    pickup_stack = 0
    max_card_id = -1
    is_reversed = 1  # -1 if reversed

    on_ready_callbacks: list[Callable[[], Awaitable[None]]] = []
    on_started_callbacks: list[Callable[[], Awaitable[None]]] = []
    on_ongoing_callbacks: list[Callable[[], Awaitable[None]]] = []
    on_finished_callbacks: list[Callable[[Player], Awaitable[None]]] = []
    on_destroyed_callbacks: list[Callable[[], Awaitable[None]]] = []
    on_initialized_callbacks: list[Callable[[], Awaitable[None]]] = []
    on_player_count_changed_callbacks: list[Callable[[], Awaitable[None]]] = []
    on_turn_completed_callbacks: list[Callable[[], Awaitable[None]]] = []

    async def start_game(self):
        if self.state != GameState.READY_TO_START:
            raise RuntimeError(f'start_game, incorrect state: {self.state}')
        self.state = GameState.STARTED
        await self.__on_started__()

        self.current_player = self.admin
        self.__refill_deck__()
        self.__put_first_card__()
        for player in self.players:
            self.__pick_up_cards__(player, 7)

        self.state = GameState.ONGOING
        await self.__on_ongoing__()

    async def process_turn(self, discord_tag: str, card_id: int | None, wild_color: Color | None):
        if self.state != GameState.ONGOING:
            raise RuntimeError(f'process_turn, incorrect state: {self.state}')
        player = next(player for player in self.players if player.discord_tag == discord_tag)
        if player.discord_tag != self.current_player.discord_tag:
            raise RuntimeError(
                f'process_turn, incorrect player: {player.discord_tag}, expected {self.current_player.discord_tag}')
        p = 1
        if card_id is None:  # draw card button pressed
            self.__pick_up_cards__(player, 1 + self.pickup_stack)
            self.pickup_stack = 0
            self.current_player = self.players[
                (self.players.index(self.current_player) + p * self.is_reversed) % len(self.players)]
            await self.__on_turn_completed__()
            return
        cards = self.playersToCards[player]
        card = next(card for card in cards if card.id == card_id)
        pickup_stack_exists = self.pickup_stack != 0
        if not card.is_plus_card and pickup_stack_exists:
            self.__pick_up_cards__(player, self.pickup_stack)
            self.pickup_stack = 0
        if not self.is_playable(card):
            raise RuntimeError()
        if isinstance(card, Reverse):
            self.is_reversed *= -1
        elif isinstance(card, Skip):
            p += 1
        elif isinstance(card, Plus):
            self.pickup_stack += 2
        elif isinstance(card, WildPlus):
            self.pickup_stack += 4
            self.current_color = wild_color
        elif isinstance(card, Wild):
            self.current_color = wild_color
        elif isinstance(card, Number):
            if card.color != self.current_color:
                self.current_color = card.color

        self.current_player = self.players[
            (self.players.index(self.current_player) + p * self.is_reversed) % len(self.players)]
        self.current_card = card
        self.playersToCards[player].remove(card)
        finished = self.__check_game_finished__(player)
        if finished:
            self.state = GameState.FINISHED
            await self.__on_finished__(player)
        else:
            await self.__on_turn_completed__()

    def __check_game_finished__(self, player: Player) -> bool:
        return len(self.playersToCards[player]) == 0

    def is_playable(self, new_card: Card) -> bool:
        if isinstance(new_card, Wild) or isinstance(new_card, WildPlus):
            return True
        if new_card.color == self.current_color:
            return True
        return isinstance(new_card, Number) and isinstance(self.current_card,
                                                           Number) and new_card.number == self.current_card.number

    def __put_first_card__(self):
        first_card = next(card for card in self.deck if isinstance(card, Number))
        self.current_card = first_card
        self.current_color = first_card.color
        self.deck.remove(first_card)

    def __pick_up_cards__(self, player: Player, count: int):
        for i in range(count):
            if len(self.deck) == 0:
                self.__refill_deck__()
            if not player in self.playersToCards:
                self.playersToCards[player] = []
            self.playersToCards[player].append(self.deck.pop())

    def __refill_deck__(self):
        for i in range(10):
            self.deck += self.__create_number_cards__(i)
            if i != 0:
                self.deck += self.__create_number_cards__(i)
        self.__create_plus_cards__()
        self.__create_wild_cards__()
        self.__create_reverse_cards__()
        self.__create_skip_cards__()
        random.shuffle(self.deck)

    def __create_reverse_cards__(self):
        for color in range(1, 5):
            for i in range(2):
                self.max_card_id += 1
                self.deck.append(Reverse(Color(color), self.max_card_id))

    def __create_skip_cards__(self):
        for color in range(1, 5):
            for i in range(2):
                self.max_card_id += 1
                self.deck.append(Skip(Color(color), self.max_card_id))

    def __create_plus_cards__(self):
        for color in range(1, 5):
            for j in range(2):
                self.max_card_id += 1
                self.deck.append(Plus(Color(color), self.max_card_id))

    def __create_wild_cards__(self):
        for i in range(4):
            self.max_card_id += 1
            self.deck.append(WildPlus(self.max_card_id))
            self.max_card_id += 1
            self.deck.append(Wild(self.max_card_id))

    def __create_number_cards__(self, number: int) -> list[Card]:
        r = Number(Color.RED, number, self.max_card_id + 1)
        b = Number(Color.GREEN, number, self.max_card_id + 2)
        g = Number(Color.GREEN, number, self.max_card_id + 3)
        y = Number(Color.YELLOW, number, self.max_card_id + 4)
        self.max_card_id += 4
        return [r, b, g, y]

    def __init__(self, admin):
        self.state = GameState.INITIALIZED
        self.admin = admin
        self.players.append(admin)

    async def add_player(self, player: Player):
        if self.state != GameState.INITIALIZED and self.state != GameState.READY_TO_START:
            raise RuntimeError(f'add_player, incorrect state: {self.state}')
        if next((p for p in self.players if player.discord_tag == p.discord_tag), None) is not None:
            raise RuntimeError(f'add_player, cannot add already existing player {player.nickname}')
        self.players.append(player)
        await self.__on_player_count_changed__()
        if self.state == GameState.INITIALIZED and len(self.players) >= 2:
            self.state = GameState.READY_TO_START
            await self.__on_ready__()

    async def remove_player(self, player: Player):
        if self.state != GameState.INITIALIZED and self.state != GameState.READY_TO_START:
            raise RuntimeError(f'remove_player, incorrect state: {self.state}')
        if self.admin == player:
            raise RuntimeError(f'remove_player, cannot remove admin from game')
        if next((p for p in self.players if p.discord_tag == player.discord_tag), None) is None:
            raise RuntimeError(f'remove_player, player is not part of the game')
        self.players.remove(player)
        await self.__on_player_count_changed__()
        if self.state == GameState.READY_TO_START and len(self.players) < 2:
            self.state = GameState.INITIALIZED
            await self.__on_initialized__()

    async def __on_ready__(self):
        if self.state == GameState.READY_TO_START:
            for callback in self.on_ready_callbacks:
                await callback()

    async def __on_started__(self):
        if self.state == GameState.STARTED:
            for callback in self.on_started_callbacks:
                await callback()

    async def __on_ongoing__(self):
        if self.state == GameState.ONGOING:
            for callback in self.on_ongoing_callbacks:
                await callback()

    async def __on_finished__(self, winner: Player):
        if self.state == GameState.FINISHED:
            for callback in self.on_finished_callbacks:
                await callback(winner)

    async def __on_destroyed__(self):
        if self.state == GameState.DESTROYED:
            for callback in self.on_destroyed_callbacks:
                await callback()

    async def __on_initialized__(self):
        if self.state == GameState.INITIALIZED:
            for callback in self.on_initialized_callbacks:
                await callback()

    async def __on_player_count_changed__(self):
        for callback in self.on_player_count_changed_callbacks:
            await callback()

    async def __on_turn_completed__(self):
        for callback in self.on_turn_completed_callbacks:
            await callback()
