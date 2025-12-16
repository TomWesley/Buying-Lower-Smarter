"""
Scoring Models API endpoints for saving and managing scoring configurations.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict

from app.db.database import get_sync_db, init_db_sync
from app.db.models import ScoringModel
from app.services.scoring import weights_to_json, weights_from_json, DEFAULT_WEIGHTS

router = APIRouter()


class CreateModelRequest(BaseModel):
    name: str
    weights: Dict[str, float]
    threshold: float = 65.0
    training_run_id: Optional[int] = None
    avg_return: Optional[float] = None
    win_rate: Optional[float] = None


class ModelResponse(BaseModel):
    id: int
    name: str
    weights: Dict[str, float]
    threshold: float
    training_run_id: Optional[int]
    avg_return: Optional[float]
    win_rate: Optional[float]
    created_at: datetime


@router.get("/", response_model=List[ModelResponse])
async def list_models():
    """List all saved scoring models"""
    init_db_sync()
    db = get_sync_db()
    try:
        models = db.query(ScoringModel).order_by(ScoringModel.created_at.desc()).all()
        return [
            ModelResponse(
                id=m.id,
                name=m.name,
                weights=weights_from_json(m.weights),
                threshold=m.threshold,
                training_run_id=m.training_run_id,
                avg_return=m.avg_return,
                win_rate=m.win_rate,
                created_at=m.created_at
            )
            for m in models
        ]
    finally:
        db.close()


@router.post("/", response_model=ModelResponse)
async def create_model(request: CreateModelRequest):
    """Save a new scoring model"""
    init_db_sync()
    db = get_sync_db()
    try:
        model = ScoringModel(
            name=request.name,
            weights=weights_to_json(request.weights),
            threshold=request.threshold,
            training_run_id=request.training_run_id,
            avg_return=request.avg_return,
            win_rate=request.win_rate
        )
        db.add(model)
        db.commit()
        db.refresh(model)

        return ModelResponse(
            id=model.id,
            name=model.name,
            weights=weights_from_json(model.weights),
            threshold=model.threshold,
            training_run_id=model.training_run_id,
            avg_return=model.avg_return,
            win_rate=model.win_rate,
            created_at=model.created_at
        )
    finally:
        db.close()


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int):
    """Get a specific scoring model"""
    db = get_sync_db()
    try:
        model = db.query(ScoringModel).filter(ScoringModel.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        return ModelResponse(
            id=model.id,
            name=model.name,
            weights=weights_from_json(model.weights),
            threshold=model.threshold,
            training_run_id=model.training_run_id,
            avg_return=model.avg_return,
            win_rate=model.win_rate,
            created_at=model.created_at
        )
    finally:
        db.close()


@router.delete("/{model_id}")
async def delete_model(model_id: int):
    """Delete a scoring model"""
    db = get_sync_db()
    try:
        model = db.query(ScoringModel).filter(ScoringModel.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        db.delete(model)
        db.commit()
        return {"message": "Model deleted"}
    finally:
        db.close()


@router.get("/defaults/weights")
async def get_default_weights():
    """Get the default scoring weights"""
    return {
        'weights': DEFAULT_WEIGHTS,
        'description': {
            'industry': 'Bonus for Technology/Healthcare companies',
            'dividends': 'Bonus for low dividend yield (<1%)',
            'reit': 'Bonus for non-REIT stocks',
            'severity_of_loss': 'Bonus for larger daily losses (>5%)',
            'ranking': 'Bonus for being the biggest loser (#1)',
            'volume': 'Bonus for high trading volume (>30M)'
        }
    }
