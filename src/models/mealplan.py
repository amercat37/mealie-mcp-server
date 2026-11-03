from typing import Optional

from pydantic import BaseModel, ConfigDict


class MealPlanEntry(BaseModel):
    # An unknown key (e.g. "entryType" for "entry_type") is an error, not silently
    # ignored — otherwise the entry would be created with the default instead
    model_config = ConfigDict(extra="forbid")

    date: str
    recipe_id: Optional[str] = None
    title: Optional[str] = None
    entry_type: str = "breakfast"
    whole_week: bool = False
