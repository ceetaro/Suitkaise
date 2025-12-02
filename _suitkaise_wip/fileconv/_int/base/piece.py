from abc import ABC
from typing import List
from ..base.formats import fmt

class Piece(ABC):

    def __init__(self, content: str, formatting: List[fmt]):
        self.content = content
        self.formatting = formatting