from enum import Enum


class Genre(str, Enum):
    FICTION = "fiction"
    NONFICTION = "nonfiction"
    SCIENCE = "science"
    FANTASY = "fantasy"
    MYSTERY = "mystery"
    BIOGRAPHY = "biography"
    HISTORY = "history"
    POETRY = "poetry"