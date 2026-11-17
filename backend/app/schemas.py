from pydantic import BaseModel, ConfigDict, Field


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=8192)


class DemoAuthRequest(BaseModel):
    username: str = Field(default="demo_player", min_length=1, max_length=64)


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SteamURLRequest(BaseModel):
    trade_url: str = Field(min_length=30, max_length=512)


class CaseOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    image_url: str
    price: int
    is_free: bool
    published_reward_name: str
    model_config = ConfigDict(from_attributes=True)


class TaskOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    task_type: str
    reward: int
    status: str
    verification_status: str


class AdminUserUpdate(BaseModel):
    is_active: bool


class TaskCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=2000)
    task_type: str = Field(default="social", max_length=32)
    reward: int = Field(ge=0, le=10000)


class CaseCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    image_url: str = Field(default="", max_length=1024)
    published_reward_id: int
    is_published: bool = True


class RewardCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    image_url: str = Field(default="", max_length=1024)
    weapon: str = Field(default="", max_length=80)
    exterior: str = Field(default="", max_length=80)
    float_value: float | None = Field(default=None, ge=0, le=1)


class SkinCreate(BaseModel):
    market_name: str = Field(min_length=2, max_length=180)
    weapon: str = Field(min_length=1, max_length=80)
    image_url: str = Field(default="", max_length=1024)
    exterior: str = Field(default="", max_length=80)
    float_value: float | None = Field(default=None, ge=0, le=1)
