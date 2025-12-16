"""
Analysis API endpoints for running backtests with a scoring model.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import csv
import io

from app.db.database import get_sync_db, init_db_sync
from app.db.models import AnalysisRun, ScoringModel
from app.services.training import run_training_analysis
from app.services.scoring import calculate_confidence_score, weights_from_json, DEFAULT_WEIGHTS

router = APIRouter()

# In-memory storage for running jobs
running_analysis_jobs: Dict[int, Dict[str, Any]] = {}


class AnalysisRequest(BaseModel):
    start_date: date
    end_date: date
    hold_years: List[int] = [2, 5]
    weights: Optional[Dict[str, float]] = None
    threshold: float = 65.0
    scoring_model_id: Optional[int] = None


class AnalysisStatusResponse(BaseModel):
    run_id: int
    status: str
    progress: float
    message: Optional[str] = None


@router.post("/run", response_model=AnalysisStatusResponse)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Start a new analysis run with a specific scoring model.
    """
    # Get weights from model or request
    weights = request.weights or DEFAULT_WEIGHTS

    if request.scoring_model_id:
        db = get_sync_db()
        try:
            model = db.query(ScoringModel).filter(ScoringModel.id == request.scoring_model_id).first()
            if model:
                weights = weights_from_json(model.weights)
        finally:
            db.close()

    # Create analysis run record
    init_db_sync()
    db = get_sync_db()

    try:
        run = AnalysisRun(
            start_date=request.start_date,
            end_date=request.end_date,
            hold_period_years=max(request.hold_years),
            run_type='analysis',
            status='pending',
            progress=0.0,
            scoring_model_id=request.scoring_model_id
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()

    # Initialize job tracking
    running_analysis_jobs[run_id] = {
        'status': 'running',
        'progress': 0,
        'message': 'Starting...',
        'results': None,
        'weights': weights,
        'threshold': request.threshold
    }

    # Run analysis in background
    background_tasks.add_task(
        run_analysis_background,
        run_id,
        datetime.combine(request.start_date, datetime.min.time()),
        datetime.combine(request.end_date, datetime.min.time()),
        request.hold_years,
        weights,
        request.threshold
    )

    return AnalysisStatusResponse(
        run_id=run_id,
        status='running',
        progress=0,
        message='Analysis started'
    )


def run_analysis_background(
    run_id: int,
    start_date: datetime,
    end_date: datetime,
    hold_years: List[int],
    weights: Dict[str, float],
    threshold: float
):
    """Background task to run analysis"""
    def progress_callback(progress: float, message: str):
        running_analysis_jobs[run_id]['progress'] = progress
        running_analysis_jobs[run_id]['message'] = message

    try:
        # Run training analysis to get all picks
        results = run_training_analysis(
            start_date,
            end_date,
            hold_years,
            progress_callback
        )

        # Apply scoring model to filter picks
        filtered_picks = []
        for pick in results['picks']:
            score = calculate_confidence_score(
                pick['ticker'],
                pick['daily_loss_pct'],
                pick['ranking'],
                pick['industry'],
                pick['dividend_yield'],
                pick['volume'],
                weights
            )
            pick['confidence_score'] = score
            if score >= threshold:
                filtered_picks.append(pick)

        # Calculate summary stats for filtered picks
        summary = calculate_analysis_summary(filtered_picks, results['picks'], hold_years)

        running_analysis_jobs[run_id]['status'] = 'completed'
        running_analysis_jobs[run_id]['progress'] = 100
        running_analysis_jobs[run_id]['message'] = 'Complete'
        running_analysis_jobs[run_id]['results'] = {
            'all_picks': results['picks'],
            'filtered_picks': filtered_picks,
            'analysis': results['analysis'],
            'summary': {
                **results['summary'],
                **summary,
                'weights': weights,
                'threshold': threshold
            }
        }

        # Update database
        db = get_sync_db()
        try:
            run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if run:
                run.status = 'completed'
                run.progress = 100
                run.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    except Exception as e:
        running_analysis_jobs[run_id]['status'] = 'failed'
        running_analysis_jobs[run_id]['message'] = str(e)

        db = get_sync_db()
        try:
            run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if run:
                run.status = 'failed'
                db.commit()
        finally:
            db.close()


def calculate_analysis_summary(filtered_picks: List[Dict], all_picks: List[Dict], hold_years: List[int]) -> Dict:
    """Calculate summary statistics for the analysis"""
    summary = {
        'filtered_count': len(filtered_picks),
        'total_count': len(all_picks),
        'filter_rate': round(len(filtered_picks) / len(all_picks) * 100, 2) if all_picks else 0
    }

    for years in hold_years:
        return_col = f'return_{years}y'
        spy_col = f'spy_return_{years}y'

        # Filtered picks stats
        filtered_returns = [p[return_col] for p in filtered_picks if p.get(return_col) is not None]
        filtered_spy = [p[spy_col] for p in filtered_picks if p.get(spy_col) is not None]

        if filtered_returns:
            summary[f'{years}y_filtered'] = {
                'count': len(filtered_returns),
                'avg_return': round(sum(filtered_returns) / len(filtered_returns), 2),
                'win_rate': round(sum(1 for r in filtered_returns if r > 0) / len(filtered_returns) * 100, 2),
                'spy_avg': round(sum(filtered_spy) / len(filtered_spy), 2) if filtered_spy else None
            }

        # All picks stats
        all_returns = [p[return_col] for p in all_picks if p.get(return_col) is not None]
        all_spy = [p[spy_col] for p in all_picks if p.get(spy_col) is not None]

        if all_returns:
            summary[f'{years}y_all'] = {
                'count': len(all_returns),
                'avg_return': round(sum(all_returns) / len(all_returns), 2),
                'win_rate': round(sum(1 for r in all_returns if r > 0) / len(all_returns) * 100, 2),
                'spy_avg': round(sum(all_spy) / len(all_spy), 2) if all_spy else None
            }

    return summary


@router.get("/{run_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(run_id: int):
    """Get the status of an analysis run"""
    if run_id in running_analysis_jobs:
        job = running_analysis_jobs[run_id]
        return AnalysisStatusResponse(
            run_id=run_id,
            status=job['status'],
            progress=job['progress'],
            message=job.get('message')
        )

    db = get_sync_db()
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Analysis run not found")

        return AnalysisStatusResponse(
            run_id=run_id,
            status=run.status,
            progress=run.progress,
            message=None
        )
    finally:
        db.close()


@router.get("/{run_id}/results")
async def get_analysis_results(run_id: int):
    """Get the results of a completed analysis run"""
    if run_id in running_analysis_jobs:
        job = running_analysis_jobs[run_id]
        if job['status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Analysis run is {job['status']}, not completed"
            )
        return job['results']

    raise HTTPException(status_code=404, detail="Analysis results not found")


@router.get("/{run_id}/export")
async def export_analysis_csv(run_id: int):
    """Export analysis results as CSV"""
    if run_id not in running_analysis_jobs:
        raise HTTPException(status_code=404, detail="Analysis results not found")

    job = running_analysis_jobs[run_id]
    if job['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Analysis not completed")

    results = job['results']
    picks = results.get('filtered_picks', [])

    # Create CSV
    output = io.StringIO()
    if picks:
        fieldnames = list(picks[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(picks)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=analysis_{run_id}.csv"}
    )
