from abc import ABC
from enum import Enum


class Color(Enum):
    RED = 1
    BLUE = 2
    YELLOW = 3
    GREEN = 4


class Card(ABC):
    id: int
    is_plus_card: bool
    added_cards: int
    color: Color


class Wild(Card):
    is_plus_card = False
    added_cards = 0
    color = None

    def __init__(self, id: int):
        self.id = id


class WildPlus(Card):
    is_plus_card = True
    added_cards = 4
    color = None

    def __init__(self, id: int):
        self.id = id


class Plus(Card):
    is_plus_card = True
    added_cards = 2

    def __init__(self, color: Color, id: int):
        self.color = color
        self.id = id


class Number(Card):
    is_plus_card = False
    added_cards = 0
    number: int

    def __init__(self, color: Color, number: int, id: int):
        self.color = color
        self.number = number
        self.id = id


class Skip(Card):
    is_plus_card = False
    added_cards = 0

    def __init__(self, color: Color, id: int):
        self.color = color
        self.id = id


class Reverse(Card):
    is_plus_card = False
    added_cards = 0

    def __init__(self, color: Color, id: int):
        self.color = color
        self.id = id
