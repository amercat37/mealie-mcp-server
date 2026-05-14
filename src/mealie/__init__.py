from .categories import CategoriesMixin
from .client import MealieClient
from .foods import FoodsMixin
from .mealplan import MealplanMixin
from .recipe import RecipeMixin
from .shopping_list import ShoppingListMixin
from .tags import TagsMixin


class MealieFetcher(
    RecipeMixin,
    CategoriesMixin,
    TagsMixin,
    FoodsMixin,
    ShoppingListMixin,
    MealplanMixin,
    MealieClient,
):
    pass
