from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.rbac import get_current_user, require_roles, write_audit_log

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Self-registration is limited to the 'personnel' role.
    Welfare officer / administrator accounts must be provisioned by an
    existing administrator via /api/auth/provision (least-privilege).
    """
    if payload.role != "personnel":
        raise HTTPException(status_code=403, detail="Self-registration is limited to personnel role.")

    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists.")

    personnel_code = payload.personnel_code
    if not personnel_code:
        count = db.query(models.PersonnelProfile).count()
        personnel_code = f"PID-{str(90000 + count + 1).zfill(5)}"

    profile = db.query(models.PersonnelProfile).filter_by(personnel_code=personnel_code).first()
    if not profile:
        profile = models.PersonnelProfile(personnel_code=personnel_code, consent_wellness_data=True)
        db.add(profile)
        db.commit()

    user = models.User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=models.RoleEnum.personnel,
        personnel_code=personnel_code,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username, "role": user.role.value})
    return schemas.Token(access_token=token, role=user.role.value, personnel_code=personnel_code)


@router.post("/provision", response_model=schemas.Token)
def provision_staff_account(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_roles("administrator")),
):
    """Administrator-only: create welfare_officer or administrator accounts."""
    if payload.role not in ("welfare_officer", "administrator"):
        raise HTTPException(status_code=400, detail="role must be welfare_officer or administrator")
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists.")

    user = models.User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=models.RoleEnum(payload.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit_log(db, admin.id, "provision_account", "users", f"created {payload.role} '{payload.username}'")

    token = create_access_token({"sub": user.username, "role": user.role.value})
    return schemas.Token(access_token=token, role=user.role.value)


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username, "role": user.role.value})
    write_audit_log(db, user.id, "login", "auth")
    return schemas.Token(access_token=token, role=user.role.value, personnel_code=user.personnel_code)


@router.get("/me")
def me(user: models.User = Depends(get_current_user)):
    return {
        "username": user.username,
        "role": user.role.value,
        "personnel_code": user.personnel_code,
    }
