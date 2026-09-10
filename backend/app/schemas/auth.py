from pydantic import BaseModel, Field, model_validator


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: int


class ProfileUpdateRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=256)
    new_username: str | None = Field(None, min_length=3, max_length=32)
    new_password: str | None = Field(None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def require_change_field(self) -> "ProfileUpdateRequest":
        if self.new_username is None and self.new_password is None:
            raise ValueError("Provide new_username and/or new_password.")
        return self
