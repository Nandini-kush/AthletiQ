from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.user import User
from app.models.session import ExerciseSession
from app.schemas.session import ExerciseSessionCreate, ExerciseSessionResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.post("", response_model=ExerciseSessionResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ExerciseSessionResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_session(
    session_in: ExerciseSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.profile:
        raise HTTPException(status_code=400, detail="User must create an athlete profile first")

    new_session = ExerciseSession(
        **session_in.model_dump(),
        athlete_id=current_user.profile.id
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@router.get("", response_model=List[ExerciseSessionResponse])
@router.get("/", response_model=List[ExerciseSessionResponse], include_in_schema=False)
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.profile:
        return []
    
    sessions = db.query(ExerciseSession).filter(ExerciseSession.athlete_id == current_user.profile.id).all()
    return sessions

@router.get("/{session_id}", response_model=ExerciseSessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.profile:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = db.query(ExerciseSession).filter(
        ExerciseSession.id == session_id,
        ExerciseSession.athlete_id == current_user.profile.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
