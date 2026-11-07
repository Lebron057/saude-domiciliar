from pydantic import BaseModel, EmailStr, Field
from typing import Literal


RoleType = Literal["familiar_paciente", "profissional_saude", "fornecedor_equipamento", "admin"]


class RegisterRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=150)
    senha: str = Field(..., min_length=6)
    role: str = Field(default="familiar_paciente")


class LoginRequest(BaseModel):
    email: str
    senha: str


class VerifyTokenRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: str
    base_url: str | None = None


class ValidateResetTokenRequest(BaseModel):
    token: str


class ResetPasswordRequest(BaseModel):
    token: str
    nova_senha: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    nome: str
    email: str
    role: str
    ativo: bool = True
    premium: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class GenericResponse(BaseModel):
    status: str
    message: str
