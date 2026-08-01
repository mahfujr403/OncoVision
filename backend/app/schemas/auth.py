"""Authentication request and response schemas."""

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.user import UserResponse

PASSWORD_MIN_LENGTH = 8


class RegisterRequest(BaseModel):
    """Payload for `POST /api/v1/auth/register`."""

    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)
    confirm_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Require at least one uppercase, lowercase, digit, and special character."""
        if not any(character.isupper() for character in value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(character.islower() for character in value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain at least one digit.")
        if not any(not character.isalnum() for character in value):
            raise ValueError("Password must contain at least one special character.")
        return value

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "RegisterRequest":
        """Ensure `password` and `confirm_password` are identical."""
        if self.password != self.confirm_password:
            raise ValueError("Password and confirmation password do not match.")
        return self


class RegisterResponse(BaseModel):
    """Response payload for a successful registration."""

    user: UserResponse


class LoginRequest(BaseModel):
    """Payload for `POST /api/v1/auth/login`."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Base token pair returned by login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class LoginResponse(TokenResponse):
    """Response payload for a successful login."""

    user: UserResponse


class RefreshRequest(BaseModel):
    """Payload for `POST /api/v1/auth/refresh` and `/logout`."""

    refresh_token: str


class RefreshResponse(TokenResponse):
    """Response payload for a successful token refresh."""
