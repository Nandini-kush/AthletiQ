from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.profile import AthleteProfile
from app.schemas.profile import AthleteProfileCreate, AthleteProfileResponse, AthleteProfileUpdate
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/profile", response_model=AthleteProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_in: AthleteProfileCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.profile:
        raise HTTPException(status_code=400, detail="Profile already exists for this user")
    
    new_profile = AthleteProfile(
        **profile_in.model_dump(),
        user_id=current_user.id
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile

@router.get("/profile", response_model=AthleteProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user)
):
    if not current_user.profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return current_user.profile

@router.put("/profile", response_model=AthleteProfileResponse)
def update_profile(
    profile_in: AthleteProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = profile_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
        
    db.commit()
    db.refresh(profile)
    return profile
