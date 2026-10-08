from pydantic import BaseModel, Field, field_validator


class PromptRequest(BaseModel):
    story_prompt: str = Field(default="", min_length=3, max_length=2000)
    character_name: str = Field(default="Hero", min_length=1, max_length=100)
    setting: str = Field(default="City", min_length=1, max_length=200)
    tone: str = Field(default="adventure", min_length=1, max_length=100)
    art_style: str = Field(default="cinematic", min_length=1, max_length=100)
    panels: int = Field(default=5, ge=1, le=12)

    @field_validator("story_prompt", "character_name", "setting", "tone", "art_style")
    @classmethod
    def _strip_values(cls, value: str) -> str:
        return value.strip()


class ComicRequest(PromptRequest):
    """Backward-compatible alias for the standard comic-generation payload."""

    prompt: str | None = None

    @property
    def effective_story_prompt(self) -> str:
        return self.story_prompt or self.prompt or "A curious traveler explores a hidden world."


class PanelOutline(BaseModel):
    panel_number: int
    title: str
    scene_description: str
    image_prompt: str


class ComicOutline(BaseModel):
    panels: list[PanelOutline] = Field(default_factory=list)


class PanelStory(BaseModel):
    panel_number: int
    narration: str
    dialogue: list[str] = Field(default_factory=list)
    caption: str = ""


class ComicStory(BaseModel):
    panels: list[PanelStory] = Field(default_factory=list)