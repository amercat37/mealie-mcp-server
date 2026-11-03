import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from recipe_times import TIME_FIELDS, parse_duration

logger = logging.getLogger("mealie-mcp")


class RecipeCommentCreate(BaseModel):
    text: str


class RecipeNutritionCreate(BaseModel):
    # Reject unknown keys so a misnamed nutrition field fails loud instead of vanishing.
    model_config = ConfigDict(extra="forbid")

    calories: Optional[str] = None
    carbohydrateContent: Optional[str] = None
    cholesterolContent: Optional[str] = None
    fatContent: Optional[str] = None
    fiberContent: Optional[str] = None
    proteinContent: Optional[str] = None
    saturatedFatContent: Optional[str] = None
    sodiumContent: Optional[str] = None
    sugarContent: Optional[str] = None
    transFatContent: Optional[str] = None
    unsaturatedFatContent: Optional[str] = None

    @field_validator("*", mode="before")
    @classmethod
    def _strip_units(cls, v: Any) -> Any:
        """Normalize nutrition values to bare numbers.

        Mealie renders the unit itself, so a value like "4.9 g" would display as
        "4.9 g g". Strip thousands separators, then keep the leading number:
        "4.9 g"->"4.9", "76 mg"->"76", "1,200 mg"->"1200", "<1 g"->"1".
        Non-numeric values (e.g. "trace", "") are preserved unchanged.
        """
        if isinstance(v, str):
            m = re.search(r"-?\d+(?:\.\d+)?", v.replace(",", ""))
            return m.group(0) if m else v
        return v


class RecipeIngredientCreate(BaseModel):
    # Nested forbid: a mis-keyed ingredient (e.g. {"amount": 5} vs {"quantity": 5})
    # errors instead of silently dropping the value.
    model_config = ConfigDict(extra="forbid")

    quantity: Optional[float] = None
    unit: Optional[str] = None  # unit name — tool resolves to ID
    food: Optional[str] = None  # food name — tool resolves to ID
    note: Optional[str] = None
    title: Optional[str] = None  # section header e.g. "For the sauce:"
    disableAmount: bool = False


class RecipeInstructionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None  # section header e.g. "Make the dough"
    text: str


class RecipeCreate(BaseModel):
    # extra="forbid": an unknown key (a field name the model doesn't map) raises a
    # validation error the LLM sees and corrects, instead of being silently discarded.
    # populate_by_name=True lets both the canonical field name AND its aliases work.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    description: Optional[str] = None
    # Aliases below accept the natural name an LLM tends to emit (plural / prefix-dropped /
    # a genuine Mealie quirk) and map it to the exact Mealie field. The JSON schema still
    # advertises the canonical name; the alias is a server-side safety net.
    recipeCategory: List[str] = Field(  # category slugs (or names — resolved case-insensitively)
        default_factory=list,
        validation_alias=AliasChoices("recipeCategory", "categories"),
    )
    tags: List[str] = Field(default_factory=lambda: ["my-recipes"])  # tag slugs; default my-recipes
    tools: List[str] = Field(default_factory=list)  # tool slugs
    recipeIngredient: List[RecipeIngredientCreate] = Field(
        default_factory=list,
        validation_alias=AliasChoices("recipeIngredient", "ingredients"),
    )
    recipeInstructions: List[RecipeInstructionCreate] = Field(
        default_factory=list,
        validation_alias=AliasChoices("recipeInstructions", "instructions"),
    )
    # Times: text with a unit ("30 minutes", "1 hour 30 minutes") or the *Seconds field.
    # Either way they are stored as Mealie's structured seconds; see time_patch().
    prepTime: Optional[str] = None
    # performTime is Mealie's active "Cook Time" field; accept the intuitive "cookTime".
    performTime: Optional[str] = Field(
        None, validation_alias=AliasChoices("performTime", "cookTime")
    )
    totalTime: Optional[str] = None
    prepTimeSeconds: Optional[int] = Field(None, ge=0)
    performTimeSeconds: Optional[int] = Field(
        None, ge=0, validation_alias=AliasChoices("performTimeSeconds", "cookTimeSeconds")
    )
    totalTimeSeconds: Optional[int] = Field(None, ge=0)
    recipeServings: Optional[float] = Field(  # number of people served (e.g. 4)
        None, validation_alias=AliasChoices("recipeServings", "servings")
    )
    recipeYieldQuantity: Optional[float] = None  # numeric total output (e.g. 12); pair with recipeYield unit
    recipeYield: Optional[str] = None  # bare yield unit only, e.g. "cookies", "cups", "loaf" (renders as "12 cookies")
    orgURL: Optional[str] = Field(  # source URL if recipe came from somewhere
        None, validation_alias=AliasChoices("orgURL", "sourceUrl", "url")
    )
    nutrition: Optional[RecipeNutritionCreate] = None
    notes: Optional[List[Dict[str, str]]] = None  # [{"title": "...", "text": "..."}]

    @model_validator(mode="before")
    @classmethod
    def _log_raw_keys(cls, data: Any) -> Any:
        """Log the raw top-level keys the caller sent, BEFORE extra='forbid' runs.

        FastMCP parses this model before create_recipe() executes, so this is the
        only place we can see the raw payload — invaluable for diagnosing which
        field names a real client actually emits (and which aliases get hit).
        """
        if isinstance(data, dict):
            logger.info({"message": "create_recipe raw input keys", "keys": sorted(data.keys())})
        return data

    @field_validator("prepTime", "performTime", "totalTime")
    @classmethod
    def _reject_bare_number(cls, v: Optional[str]) -> Optional[str]:
        """Fail loud on a unit-less time like "45" (minutes? hours?) at validation, so
        the caller corrects it before any recipe is created."""
        parse_duration(v)  # raises BareNumberError (a ValueError) for a bare number
        return v

    def time_patch(self) -> Dict[str, Any]:
        """Mealie PATCH fields for the recipe times.

        A duration is stored only as seconds, matching recipes Mealie migrated; the text
        field is used only for a value that isn't a duration ("overnight"). An explicit
        *Seconds value wins over text for the same time. Zero means no time.
        """
        patch: Dict[str, Any] = {}
        for field in TIME_FIELDS:
            seconds = getattr(self, f"{field}Seconds")
            text = getattr(self, field)
            if seconds is None and text:
                seconds = parse_duration(text)
                if seconds is None:
                    patch[field] = text.strip()
                    continue
            if seconds:
                patch[f"{field}Seconds"] = seconds
        return patch


class RecipeComment(BaseModel):
    id: Optional[str] = None
    recipeId: Optional[str] = None
    userId: Optional[str] = None
    text: str
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class IngredientUnit(BaseModel):
    id: Optional[str] = None
    name: str
    pluralName: Optional[str] = None
    description: str = ""
    extras: Optional[Dict[str, Any]] = None
    fraction: bool = True
    abbreviation: str = ""
    pluralAbbreviation: Optional[str] = ""
    useAbbreviation: bool = False
    aliases: List[Any] = Field(default_factory=list)
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class IngredientFood(BaseModel):
    id: Optional[str] = None
    name: str
    pluralName: Optional[str] = None
    description: str = ""
    extras: Optional[Dict[str, Any]] = None
    labelId: Optional[str] = None
    label: Optional[Any] = None
    aliases: List[Any] = Field(default_factory=list)
    householdsWithIngredientFood: List[str] = Field(default_factory=list)
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class RecipeIngredient(BaseModel):
    quantity: Optional[float] = None
    unit: Optional[IngredientUnit] = None
    food: Optional[IngredientFood] = None
    note: Optional[str] = None
    isFood: Optional[bool] = True
    disableAmount: Optional[bool] = False
    display: Optional[str] = None
    title: Optional[str] = None
    originalText: Optional[str] = None
    referenceId: Optional[str] = None


class RecipeInstruction(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    text: str
    ingredientReferences: List[str] = Field(default_factory=list)


class RecipeNutrition(BaseModel):
    calories: Optional[str] = None
    carbohydrateContent: Optional[str] = None
    cholesterolContent: Optional[str] = None
    fatContent: Optional[str] = None
    fiberContent: Optional[str] = None
    proteinContent: Optional[str] = None
    saturatedFatContent: Optional[str] = None
    sodiumContent: Optional[str] = None
    sugarContent: Optional[str] = None
    transFatContent: Optional[str] = None
    unsaturatedFatContent: Optional[str] = None


class RecipeSettings(BaseModel):
    public: bool = False
    showNutrition: bool = False
    showAssets: bool = False
    landscapeView: bool = False
    disableComments: bool = False
    disableAmount: bool = False
    locked: bool = False


class Recipe(BaseModel):
    id: str
    userId: str
    householdId: str
    groupId: str
    name: str
    slug: str
    image: Optional[str] = None
    recipeServings: Optional[float] = None
    recipeYieldQuantity: Optional[float] = 0
    recipeYield: Optional[str] = None
    totalTime: Optional[str] = None
    prepTime: Optional[str] = None
    cookTime: Optional[str] = None
    performTime: Optional[str] = None
    description: Optional[str] = None
    recipeCategory: List[Any] = Field(default_factory=list)
    tags: List[Any] = Field(default_factory=list)
    tools: List[Any] = Field(default_factory=list)
    rating: Optional[float] = None
    orgURL: Optional[str] = None
    dateAdded: str
    dateUpdated: str
    createdAt: str
    updatedAt: str
    lastMade: Optional[str] = None
    recipeIngredient: List[RecipeIngredient] = Field(default_factory=list)
    recipeInstructions: List[RecipeInstruction] = Field(default_factory=list)
    nutrition: RecipeNutrition = Field(default_factory=RecipeNutrition)
    settings: RecipeSettings = Field(default_factory=RecipeSettings)
    assets: List[Any] = Field(default_factory=list)
    notes: List[Any] = Field(default_factory=list)
    extras: Dict[str, Any] = Field(default_factory=dict)
    comments: List[Any] = Field(default_factory=list)
