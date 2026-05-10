from typing import Dict, List, Any

def _suggest_inputs_from_signals(schedule: Dict[str, Any]) -> Dict[str, List[int]]:
    suggestions: Dict[str, List[int]] = {}
    signals = schedule.get('detected_signals') if isinstance(schedule, dict) else None
    if not signals:
        return suggestions

    joined = ' '.join(signals).lower()
    if '24_hour' in joined or '24h_coverage' in joined or '24h' in joined:
        suggestions['shifts_per_day'] = [3]
        suggestions['hours_per_day'] = [8]
    if 'day_and_night' in joined or 'day-night' in joined:
        suggestions.setdefault('shifts_per_day', []).append(2)
        suggestions.setdefault('hours_per_day', []).append(12)

    return suggestions


def validate_extracted_tender(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Validate required fields. Return None-like dict for completeness or structured error payload."""
    missing: List[str] = []

    # shifts and hours are exposed at top level as integers (or None)
    shifts = extracted.get('shifts_per_day')
    hours = extracted.get('hours_per_day')

    if shifts is None:
        missing.append('shifts_per_day')
    if hours is None:
        missing.append('hours_per_day')

    # workers
    workforce = extracted.get('workforce', {}) or {}
    workers = workforce.get('total_workers') if isinstance(workforce, dict) else None
    if workers is None:
        missing.append('workers')

    # duration: try multiple fields
    duration = extracted.get('duration') or {}
    duration_months = None
    if isinstance(duration, dict):
        duration_months = duration.get('months')
    if duration_months is None:
        duration_months = extracted.get('duration_months')
    if duration_months is None:
        missing.append('duration')

    if missing:
        schedule = extracted.get('schedule') or {}
        payload = {
            'status': 'incomplete',
            'missing_fields': missing,
            'extracted_data': {
                'shifts_per_day': shifts,
                'hours_per_day': hours,
                'workers': workers,
                'duration': duration_months
            },
            'detected_signals': schedule.get('detected_signals', []),
            'suggested_inputs': _suggest_inputs_from_signals(schedule)
        }
        return payload

    return {'status': 'complete'}
