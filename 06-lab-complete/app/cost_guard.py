"""
Cost guard (tiêu chí 8) - giới hạn chi phí LLM theo ngày/tháng.
"""
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006
BUDGET_KEY = "cost:daily"


def check_budget() -> None:
    if r is None:
        return
    try:
        current = float(r.get(BUDGET_KEY) or 0)
        if current >= settings.daily_budget_usd:
            raise HTTPException(status_code=402, detail="Daily budget exceeded")
    except HTTPException:
        raise
    except Exception:
        pass


def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens / 1000) * PRICE_INPUT_PER_1K + (output_tokens / 1000) * PRICE_OUTPUT_PER_1K
    if r is not None:
        try:
            pipe = r.pipeline()
            pipe.incrbyfloat(BUDGET_KEY, cost)
            pipe.expire(BUDGET_KEY, 86400)
            pipe.execute()
        except Exception:
            pass
    return cost
