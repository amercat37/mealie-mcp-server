from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RecipeCommentCreate(BaseModel):
    text: str


class RecipeNutritionCreate(BaseModel):
    calories: Optional[str] = None
    carbohydrateContent: Optional[str] = None
    fatContent: Optional[str] = None
    fiberContent: Optional[str] = None
    proteinContent: Optional[str] = None
    sodiumContent: Optional[str] = None
    sugarContent: Optional[str] = None


class RecipeIngredientCreate(BaseModel):
    quantity: Optional[float] = None
    unit: Optional[str] = None  # unit name — tool resolves to ID
    food: Optional[str] = None  # food name — tool resolves to ID
    note: Optional[str] = None
    title: Optional[str] = None  # section header e.g. "For the sauce:"
    disableAmount: bool = False


class RecipeInstructionCreate(BaseModel):
    title: Optional[str] = None  # section header e.g. "Make the dough"
    text: str


class RecipeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    recipeCategory: List[str] = Field(default_factory=list)  # category slugs
    tags: List[str] = Field(default_factory=lambda: ["my-recipes"])  # tag slugs; default my-recipes
    tools: List[str] = Field(default_factory=list)  # tool slugs
    recipeIngredient: List[RecipeIngredientCreate] = Field(default_factory=list)
    recipeInstructions: List[RecipeInstructionCreate] = Field(default_factory=list)
    prepTime: Optional[str] = None  # ISO 8601 e.g. "PT30M"
    performTime: Optional[str] = None  # active cook time
    totalTime: Optional[str] = None
    recipeYield: Optional[str] = None  # e.g. "4 servings"
    recipeServings: Optional[int] = None
    orgURL: Optional[str] = None  # source URL if recipe came from somewhere
    nutrition: Optional[RecipeNutritionCreate] = None
    notes: Optional[List[Dict[str, str]]] = None  # [{"title": "...", "text": "..."}]


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
    recipeServings: Optional[int] = None
    recipeYieldQuantity: Optional[int] = 0
    recipeYield: Optional[str] = None
    totalTime: Optional[int] = None
    prepTime: Optional[int] = None
    cookTime: Optional[int] = None
    performTime: Optional[int] = None
    description: Optional[str] = None
    recipeCategory: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
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
