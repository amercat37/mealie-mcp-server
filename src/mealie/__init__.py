from .categories import CategoriesMixin
from .client import MealieClient
from .foods import FoodsMixin
from .group import GroupMixin
from .mealplan import MealplanMixin
from .recipe import RecipeMixin
from .shopping_list import ShoppingListMixin
from .tags import TagsMixin
from .user import UserMixin


class MealieFetcher(
    RecipeMixin,
    CategoriesMixin,
    TagsMixin,
    FoodsMixin,
    ShoppingListMixin,
    MealplanMixin,
    UserMixin,
    GroupMixin,
    MealieClient,
):
    pass
