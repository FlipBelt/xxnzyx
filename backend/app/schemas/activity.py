from pydantic import BaseModel, Field


class ParticipantAuthRequest(BaseModel):
    channel: str = Field(pattern="^(wechat|h5|dingtalk)$")
    external_id: str = Field(min_length=1, max_length=160)
    activity_slug: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=80)
    number_plate: str = Field(min_length=1, max_length=50)


class RegistrationCreate(BaseModel):
    activity_slug: str = Field(min_length=1, max_length=80)
    channel: str = Field(pattern="^(wechat|h5|dingtalk)$")
    external_id: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=80)
    phone: str = Field(pattern=r"^\d{11}$")
    number_plate: str = Field(min_length=1, max_length=50)


class AdminRegistrationCreate(BaseModel):
    """现场补录使用，与普通报名共享同一份参赛数据。"""

    name: str = Field(min_length=1, max_length=80)
    phone: str = Field(pattern=r"^\d{11}$")
    number_plate: str = Field(min_length=1, max_length=50)


class ScoreEntry(BaseModel):
    score_item_id: int
    quantity: int = Field(ge=0, le=1000)


class ScoreCreate(BaseModel):
    registration_id: int
    items: list[ScoreEntry] = Field(min_length=1)


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class RewardTierUpdate(BaseModel):
    min_score: int = Field(ge=0)
    max_score: int | None = Field(default=None, ge=0)
    title: str = Field(min_length=1, max_length=80)
    prize_name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    display_order: int = Field(ge=0, default=0)


class ScoreItemUpdate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=80)
    points: int = Field(ge=0, le=1000)
    max_quantity: int | None = Field(default=None, ge=0, le=1000)
    is_required: bool = False
    is_hidden_bonus: bool = False
    appear_at_seconds_remaining: int | None = Field(default=None, ge=0, le=3600)
    display_order: int = Field(ge=0, default=0)


class ActivitySettingsUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    status: str = Field(pattern="^(draft|active|ended)$")
    challenge_duration_seconds: int = Field(ge=1, le=3600)
    challenge_limit: int = Field(ge=1, le=100)
    draw_threshold: int = Field(ge=0, le=10000)
    leaderboard_name_mode: str = Field(pattern="^(plate_masked_name|plate_only|masked_name)$")
    rules_text: str | None = None


class MediaAssetUpdate(BaseModel):
    kind: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=100)
    public_url: str = Field(min_length=1, max_length=1000)
    object_key: str | None = Field(default=None, max_length=500)
    mime_type: str | None = Field(default=None, max_length=100)
