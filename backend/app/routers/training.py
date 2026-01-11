"""
Training API endpoints for running analysis and discovering optimal scoring weights.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import json

from app.db.database import get_sync_db, init_db_sync
from app.db.models import AnalysisRun, StockPick, ScoringModel
from app.services.training import run_training_analysis, evaluate_model, analyze_training_results
from app.services.scoring import weights_to_json, DEFAULT_WEIGHTS

router = APIRouter()

# In-memory storage for running jobs (for progress tracking during execution)
running_jobs: Dict[int, Dict[str, Any]] = {}


class TrainingRequest(BaseModel):
    start_date: date
    end_date: date
    hold_years: List[int] = [2, 5]


class TrainingStatusResponse(BaseModel):
    run_id: int
    status: str
    progress: float
    message: Optional[str] = None


class EvaluateModelRequest(BaseModel):
    picks: List[Dict[str, Any]]
    weights: Dict[str, float]
    threshold: float = 65.0
    hold_years: int = 2


@router.post("/run", response_model=TrainingStatusResponse)
async def start_training(request: TrainingRequest, background_tasks: BackgroundTasks):
    """
    Start a new training run.
    This fetches historical data and analyzes biggest loser patterns.
    Results are persisted to the database for later use.
    """
    # Create analysis run record
    init_db_sync()
    db = get_sync_db()

    try:
        run = AnalysisRun(
            start_date=request.start_date,
            end_date=request.end_date,
            hold_period_years=max(request.hold_years),
            run_type='training',
            status='pending',
            progress=0.0
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()

    # Initialize job tracking
    running_jobs[run_id] = {
        'status': 'running',
        'progress': 0,
        'message': 'Starting...',
        'results': None
    }

    # Run analysis in background
    background_tasks.add_task(
        run_training_background,
        run_id,
        datetime.combine(request.start_date, datetime.min.time()),
        datetime.combine(request.end_date, datetime.min.time()),
        request.hold_years
    )

    return TrainingStatusResponse(
        run_id=run_id,
        status='running',
        progress=0,
        message='Training started'
    )


def run_training_background(
    run_id: int,
    start_date: datetime,
    end_date: datetime,
    hold_years: List[int]
):
    """Background task to run training analysis and persist results to database"""
    def progress_callback(progress: float, message: str):
        running_jobs[run_id]['progress'] = progress
        running_jobs[run_id]['message'] = message

    try:
        results = run_training_analysis(
            start_date,
            end_date,
            hold_years,
            progress_callback
        )

        # Save picks to database
        db = get_sync_db()
        try:
            for pick_data in results['picks']:
                pick = StockPick(
                    run_id=run_id,
                    loser_date=datetime.strptime(pick_data['loser_date'], '%Y-%m-%d').date(),
                    purchase_date=datetime.strptime(pick_data['purchase_date'], '%Y-%m-%d').date() if pick_data.get('purchase_date') else None,
                    purchase_price=pick_data.get('purchase_price'),
                    ticker=pick_data['ticker'],
                    daily_loss_pct=pick_data['daily_loss_pct'],
                    ranking=pick_data['ranking'],
                    industry=pick_data.get('industry'),
                    dividend_yield=pick_data.get('dividend_yield'),
                    volume=pick_data.get('volume'),
                    confidence_score=pick_data.get('confidence_score'),
                    return_2y=pick_data.get('return_2y'),
                    return_5y=pick_data.get('return_5y'),
                    spy_return_2y=pick_data.get('spy_return_2y'),
                    spy_return_5y=pick_data.get('spy_return_5y'),
                )
                db.add(pick)

            # Update run status
            run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if run:
                run.status = 'completed'
                run.progress = 100
                run.completed_at = datetime.utcnow()

            # Auto-create a scoring model from the discovered formula
            model_created = False
            if results.get('analysis'):
                # Use 2Y analysis if available, otherwise 5Y
                analysis_key = '2y' if '2y' in results['analysis'] else '5y' if '5y' in results['analysis'] else None
                if analysis_key and results['analysis'][analysis_key].get('suggested_weights'):
                    suggested = results['analysis'][analysis_key]['suggested_weights']
                    formula = suggested.get('formula', {})

                    if formula:
                        # Count existing models to generate name
                        model_count = db.query(ScoringModel).count()
                        model_name = f"Model {model_count + 1} (Training Run #{run_id})"

                        # Get performance stats if available
                        avg_return = results['analysis'][analysis_key].get('avg_return')
                        win_rate = results['analysis'][analysis_key].get('win_rate')

                        # Create the model
                        new_model = ScoringModel(
                            name=model_name,
                            training_run_id=run_id,
                            formula=json.dumps(formula),
                            avg_return=avg_return,
                            win_rate=win_rate,
                        )
                        db.add(new_model)
                        model_created = True

            db.commit()
        finally:
            db.close()

        # Keep results in memory for immediate access
        running_jobs[run_id]['status'] = 'completed'
        running_jobs[run_id]['progress'] = 100
        running_jobs[run_id]['message'] = 'Complete - Model created' if model_created else 'Complete'
        running_jobs[run_id]['results'] = results

    except Exception as e:
        running_jobs[run_id]['status'] = 'failed'
        running_jobs[run_id]['message'] = str(e)

        # Update database
        db = get_sync_db()
        try:
            run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if run:
                run.status = 'failed'
                db.commit()
        finally:
            db.close()


@router.get("/{run_id}/status", response_model=TrainingStatusResponse)
async def get_training_status(run_id: int):
    """Get the status of a training run"""
    if run_id in running_jobs:
        job = running_jobs[run_id]
        return TrainingStatusResponse(
            run_id=run_id,
            status=job['status'],
            progress=job['progress'],
            message=job.get('message')
        )

    # Check database
    db = get_sync_db()
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Training run not found")

        return TrainingStatusResponse(
            run_id=run_id,
            status=run.status,
            progress=run.progress,
            message=None
        )
    finally:
        db.close()


@router.get("/{run_id}/results")
async def get_training_results(run_id: int):
    """
    Get the results of a completed training run.
    First checks in-memory cache, then loads from database if needed.
    """
    # Check in-memory first (for recently completed runs)
    if run_id in running_jobs:
        job = running_jobs[run_id]
        if job['status'] == 'completed' and job['results']:
            return job['results']

    # Load from database
    db = get_sync_db()
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Training run not found")

        if run.status != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Training run is {run.status}, not completed"
            )

        # Load picks from database
        picks = db.query(StockPick).filter(StockPick.run_id == run_id).all()

        # Convert to dict format
        picks_data = []
        for pick in picks:
            picks_data.append({
                'loser_date': pick.loser_date.strftime('%Y-%m-%d'),
                'purchase_date': pick.purchase_date.strftime('%Y-%m-%d') if pick.purchase_date else None,
                'purchase_price': pick.purchase_price,
                'ticker': pick.ticker,
                'daily_loss_pct': pick.daily_loss_pct,
                'ranking': pick.ranking,
                'industry': pick.industry,
                'dividend_yield': pick.dividend_yield,
                'volume': pick.volume,
                'confidence_score': pick.confidence_score,
                'return_2y': pick.return_2y,
                'return_5y': pick.return_5y,
                'spy_return_2y': pick.spy_return_2y,
                'spy_return_5y': pick.spy_return_5y,
            })

        # Determine hold years from available data
        hold_years = []
        if any(p['return_2y'] is not None for p in picks_data):
            hold_years.append(2)
        if any(p['return_5y'] is not None for p in picks_data):
            hold_years.append(5)

        # Re-run analysis on loaded data
        analysis = analyze_training_results(picks_data, hold_years)

        return {
            'picks': picks_data,
            'analysis': analysis,
            'summary': {
                'start_date': run.start_date.strftime('%Y-%m-%d'),
                'end_date': run.end_date.strftime('%Y-%m-%d'),
                'total_trading_days': len(set(p['loser_date'] for p in picks_data)),
                'total_picks': len(picks_data),
                'hold_periods': hold_years
            }
        }
    finally:
        db.close()


@router.get("/runs")
async def list_training_runs():
    """List all training runs"""
    db = get_sync_db()
    try:
        runs = db.query(AnalysisRun).filter(
            AnalysisRun.run_type == 'training'
        ).order_by(AnalysisRun.created_at.desc()).all()

        return [
            {
                'id': run.id,
                'start_date': run.start_date.strftime('%Y-%m-%d'),
                'end_date': run.end_date.strftime('%Y-%m-%d'),
                'status': run.status,
                'created_at': run.created_at.isoformat(),
                'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                'pick_count': db.query(StockPick).filter(StockPick.run_id == run.id).count()
            }
            for run in runs
        ]
    finally:
        db.close()


@router.delete("/{run_id}")
async def delete_training_run(run_id: int):
    """Delete a training run and its picks"""
    db = get_sync_db()
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Training run not found")

        db.delete(run)  # Cascade will delete picks
        db.commit()

        # Remove from memory if present
        if run_id in running_jobs:
            del running_jobs[run_id]

        return {"message": "Training run deleted"}
    finally:
        db.close()


@router.post("/evaluate")
async def evaluate_scoring_model(request: EvaluateModelRequest):
    """
    Evaluate a scoring model against training data.
    Allows testing different weights and thresholds.
    """
    results = evaluate_model(
        request.picks,
        request.weights,
        request.threshold,
        request.hold_years
    )
    return results


@router.get("/defaults")
async def get_default_weights():
    """Get the default scoring weights"""
    return {
        'weights': DEFAULT_WEIGHTS,
        'threshold': 65.0
    }
