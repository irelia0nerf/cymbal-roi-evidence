"""Motor determinístico de ROI v1 do estudo FoundLab; sem rede, IA ou dados reais."""

from decimal import Decimal, ROUND_HALF_UP, localcontext
import re

MONEY = re.compile(r"(?:0|[1-9][0-9]{0,14})(?:\.[0-9]{1,2})?\Z")


def _keys(obj, expected, label):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError(f"{label}: campos inválidos")


def _amount(value, label):
    if not isinstance(value, str) or not MONEY.fullmatch(value):
        raise ValueError(f"{label}: use string decimal não negativa, até 2 casas")
    return Decimal(value)


def _display(value):
    return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")


def calculate(payload):
    """Valida o contrato, calcula cada cenário e retorna JSON serializável."""
    with localcontext() as context:
        context.prec = 50
        return _calculate(payload)


def _calculate(payload):
    _keys(payload, {"currency", "scenarios", "assumptions"}, "entrada")
    if payload["currency"] != "BRL":
        raise ValueError("currency: apenas BRL neste exemplo")
    assumptions = payload["assumptions"]
    if not isinstance(assumptions, list) or not assumptions or any(
        not isinstance(item, str) or not item.strip() for item in assumptions
    ):
        raise ValueError("assumptions: lista não vazia de textos")
    scenarios = payload["scenarios"]
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 100:
        raise ValueError("scenarios: forneça de 1 a 100 cenários")
    seen = set()
    results = []
    horizon = None
    for scenario in scenarios:
        _keys(scenario, {"name", "initial_investment", "annual_benefits",
                         "annual_operating_costs"}, "cenário")
        name = scenario["name"]
        if not isinstance(name, str) or not name.strip() or name.strip() in seen:
            raise ValueError("name: nome não vazio e único")
        name = name.strip()
        seen.add(name)
        investment = _amount(scenario["initial_investment"], "initial_investment")
        if investment <= 0:
            raise ValueError("initial_investment: deve ser maior que zero")
        benefits = scenario["annual_benefits"]
        costs = scenario["annual_operating_costs"]
        if not isinstance(benefits, list) or not isinstance(costs, list):
            raise ValueError("benefícios e custos devem ser listas")
        if not 1 <= len(benefits) <= 30 or len(benefits) != len(costs):
            raise ValueError("horizonte: de 1 a 30 anos, listas de mesmo tamanho")
        if horizon is not None and len(benefits) != horizon:
            raise ValueError("cenários devem ter o mesmo horizonte")
        horizon = len(benefits)
        b = [_amount(x, "annual_benefits") for x in benefits]
        c = [_amount(x, "annual_operating_costs") for x in costs]
        accumulated = Decimal(0)
        payback = None
        for year, (benefit, cost) in enumerate(zip(b, c)):
            net = benefit - cost
            previous = accumulated
            accumulated += net
            if payback is None and net > 0 and accumulated >= investment:
                payback = (Decimal(year) + (investment - previous) / net) * 12
        result = accumulated - investment
        results.append({
            "name": name,
            "horizon_years": horizon,
            "initial_investment": _display(investment),
            "total_benefits": _display(sum(b, Decimal(0))),
            "total_operating_costs": _display(sum(c, Decimal(0))),
            "net_benefits_before_investment": _display(accumulated),
            "net_result_after_investment": _display(result),
            "roi_percent": _display(result / investment * 100),
            "simple_payback_months": None if payback is None else _display(payback),
        })
    return {"formula_version": "simple-roi-v1", "currency": "BRL",
            "assumptions": list(assumptions), "scenarios": results}
