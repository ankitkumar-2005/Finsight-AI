from datetime import date

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


CATEGORY_GROUPS = {
    "Food": ("food", "dining", "restaurant", "grocer", "grocery", "cafe", "coffee"),
    "Shopping": ("shop", "retail", "clothing", "apparel", "electronics", "marketplace"),
    "Travel": ("travel", "transport", "taxi", "uber", "flight", "hotel", "fuel", "commute"),
    "Entertainment": ("entertain", "stream", "movie", "music", "game", "subscription"),
    "Bills & subscriptions": ("bill", "utility", "rent", "electric", "internet", "phone", "insurance", "subscription"),
}


def _normalize(records):
    frame = pd.DataFrame(records)
    if frame.empty:
        return pd.DataFrame(columns=["transaction_date", "amount", "category", "type", "title"])
    required = {"transaction_date", "amount", "category", "type"}
    if not required.issubset(frame.columns):
        raise ValueError("Transaction data is missing required fields.")
    frame["transaction_date"] = pd.to_datetime(frame["transaction_date"], format="mixed", errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame["category"] = frame["category"].fillna("").astype(str)
    frame["type"] = frame["type"].fillna("").astype(str).str.lower()
    frame["title"] = frame.get("title", pd.Series("", index=frame.index)).fillna("").astype(str)
    frame = frame.dropna(subset=["transaction_date", "amount"])
    frame = frame[(frame["amount"] > 0) & frame["type"].isin(["income", "expense"])]
    frame["month"] = frame["transaction_date"].dt.to_period("M")
    return frame


def _forecast(monthly_expenses, current_period):
    if len(monthly_expenses) < 4:
        return {"available": False, "reason": "Add transactions across at least four distinct months to build a useful forecast.", "months_of_history": len(monthly_expenses)}
    values = monthly_expenses["expenses"].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        return {"available": False, "reason": "The recorded amounts are not suitable for a reliable estimate yet.", "months_of_history": len(values)}
    x = np.arange(len(values), dtype=float).reshape(-1, 1)
    model = LinearRegression().fit(x, values)
    predicted = max(0.0, float(model.predict(np.array([[len(values)]], dtype=float))[0]))
    fitted = model.predict(x)
    residuals = values - fitted
    mae = float(np.mean(np.abs(residuals)))
    relative_error = mae / max(float(np.mean(values)), 1.0)
    confidence = "low" if len(values) < 6 or relative_error > 0.35 else "moderate"
    next_month = (current_period + 1).strftime("%Y-%m")
    return {
        "available": True,
        "month": next_month,
        "estimated_expenses": round(predicted, 2),
        "history_months": len(values),
        "method": "linear trend over monthly recorded expenses",
        "mean_absolute_error": round(mae, 2),
        "confidence": confidence,
        "limitation": "An estimate from past recorded spending; unusual events, missing transactions, and future changes are not known. It is not guaranteed.",
        "historical": [{"month": str(idx), "expenses": round(float(value), 2)} for idx, value in monthly_expenses["expenses"].items()],
    }


def analyze_transactions(records, today=None):
    frame = _normalize(records)
    today = pd.Timestamp(today or date.today())
    current_period = today.to_period("M")
    previous_period = current_period - 1
    expenses = frame[frame["type"] == "expense"].copy()

    monthly = expenses.groupby("month")["amount"].sum().sort_index()
    if not monthly.empty and monthly.index[-1] > current_period:
        monthly = monthly.loc[monthly.index <= current_period]
    if not monthly.empty:
        all_months = pd.period_range(monthly.index.min(), current_period, freq="M")
        monthly = monthly.reindex(all_months, fill_value=0.0)
    monthly_frame = pd.DataFrame({"expenses": monthly})
    forecast = _forecast(monthly_frame, current_period)

    groups = []
    for name, terms in CATEGORY_GROUPS.items():
        mask = expenses["category"].str.lower().apply(lambda category: any(term in category for term in terms))
        current = float(expenses.loc[mask & (expenses["month"] == current_period), "amount"].sum())
        previous = float(expenses.loc[mask & (expenses["month"] == previous_period), "amount"].sum())
        if current or previous:
            delta = current - previous
            pct = (delta / previous * 100) if previous else None
            groups.append({"category": name, "current": round(current, 2), "previous": round(previous, 2), "change": round(delta, 2), "change_percent": round(pct, 1) if pct is not None else None})

    recommendations = []
    for item in groups:
        if item["previous"] > 0 and item["change_percent"] is not None and item["change_percent"] >= 20:
            recommendations.append({"title": f"Review your {item['category'].lower()} spending", "text": f"You spent {item['change_percent']:.0f}% more on {item['category'].lower()} this month than last month ({item['current']:.2f} vs {item['previous']:.2f}). Reducing this category could help you save more.", "category": item["category"], "change_percent": item["change_percent"]})
    if not recommendations:
        recommendations.append({"title": "Keep tracking to personalize suggestions", "text": "Suggestions appear when recorded spending shows a meaningful category change between this month and last month."})

    unusual = []
    for category, group in expenses.groupby("category", dropna=False):
        history = group.sort_values("transaction_date")
        if len(history) < 5:
            continue
        values = history["amount"].to_numpy(dtype=float)
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        threshold = q3 + 1.5 * iqr if iqr > 0 else q3 * 2
        candidates = history[history["amount"] > threshold]
        for _, row in candidates.tail(20).iterrows():
            raw_id = row.get("id")
            transaction_id = int(raw_id) if pd.notna(raw_id) else None
            unusual.append({"id": transaction_id, "title": row["title"], "category": str(category), "amount": round(float(row["amount"]), 2), "transaction_date": row["transaction_date"].date().isoformat(), "reason": f"This is above the category's unusual-spending threshold ({threshold:.2f}) based on {len(history)} recorded transactions.", "notice": "A statistical outlier only; this does not mean fraud."})

    current_income = float(frame.loc[(frame["type"] == "income") & (frame["month"] == current_period), "amount"].sum())
    current_expenses = float(expenses.loc[expenses["month"] == current_period, "amount"].sum())
    previous_income = float(frame.loc[(frame["type"] == "income") & (frame["month"] == previous_period), "amount"].sum())
    previous_expenses = float(expenses.loc[expenses["month"] == previous_period, "amount"].sum())
    savings_rate = ((current_income - current_expenses) / current_income * 100) if current_income else 0.0
    if current_income:
        health = "positive" if current_expenses <= current_income else "attention"
        health_text = f"This month, recorded income is {current_income:.2f} and recorded expenses are {current_expenses:.2f}; net recorded savings rate is {savings_rate:.1f}%."
    else:
        health = "incomplete"
        health_text = "Record income as well as expenses to calculate a meaningful savings rate."

    return {
        "period": {"current_month": str(current_period), "previous_month": str(previous_period)},
        "comparison": {"income": {"current": round(current_income, 2), "previous": round(previous_income, 2)}, "expenses": {"current": round(current_expenses, 2), "previous": round(previous_expenses, 2)}, "savings_rate_percent": round(savings_rate, 1)},
        "monthly_spending": groups,
        "forecast": forecast,
        "recommendations": recommendations,
        "unusual_transactions": unusual,
        "financial_health": {"status": health, "summary": health_text, "disclaimer": "This summary uses only transactions recorded in FinSight and is informational, not financial advice."},
        "transaction_count": len(frame),
    }
