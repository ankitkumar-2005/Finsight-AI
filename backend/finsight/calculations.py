from decimal import Decimal


def budget_progress(limit, spent):
    limit = Decimal(str(limit or 0))
    spent = Decimal(str(spent or 0))
    remaining = limit - spent
    percent = (spent * Decimal("100") / limit) if limit > 0 else (Decimal("100") if spent > 0 else Decimal("0"))
    if spent > limit:
        level = "exceeded"
        message = f"Over budget by {remaining.copy_abs():.2f}."
    elif spent == limit and limit > 0:
        level = "reached"
        message = "Budget limit reached."
    elif percent >= Decimal("80"):
        level = "warning"
        message = "80% or more of this budget has been used."
    else:
        level = "on_track"
        message = ""
    return {
        "remaining": float(remaining),
        "usage_percent": float(percent),
        "alert_level": level,
        "alert_message": message,
    }


def savings_percentage(income, expenses):
    income = Decimal(str(income or 0))
    expenses = Decimal(str(expenses or 0))
    if income <= 0:
        return 0.0
    return float(((income - expenses) * Decimal("100") / income).quantize(Decimal("0.01")))
