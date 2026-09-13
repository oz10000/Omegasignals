# report_generator.py
"""Genera el reporte de ranking Omega + Star Trade prediction."""
import pandas as pd
from typing import List
from omega_ranker import OmegaSignal
from star_trade_predictor import StarTradePrediction


def to_dataframe(signals: List[OmegaSignal]) -> pd.DataFrame:
    rows = []
    for i, s in enumerate(signals, 1):
        rows.append({
            'Rank': f'#{i}',
            'Activo': s.symbol,
            'Dir': s.direction,
            'Tier': s.tier,
            'Ω Score': round(s.omega_score, 2),
            'WR Est.': f"{s.estimated_wr*100:.1f}%",
            'PF Est.': round(s.estimated_pf, 2),
            'Entrada': round(s.entry_price, 6),
            'SL': round(s.stop_loss, 6),
            'TP': round(s.take_profit, 6),
            'BE': round(s.break_even_price, 6),
            'Trailing': f"{s.trailing_distance*100:.2f}%",
            'Leverage': f"{s.leverage_max}x",
            'Régimen': s.regime,
        })
    return pd.DataFrame(rows)


def to_text(signals: List[OmegaSignal]) -> str:
    lines = ["=" * 70, "  D.A.P.S-SIGNALS Ω — RANKING OMEGA", "=" * 70, ""]
    for i, s in enumerate(signals, 1):
        lines.append(f"#{i}  {s.symbol}  {s.direction}  [{s.tier}]")
        lines.append(f"    Ω Score:      {s.omega_score:.2f}")
        lines.append(f"    WR estimado:  {s.estimated_wr*100:.1f}%")
        lines.append(f"    PF estimado:  {s.estimated_pf:.2f}")
        lines.append(f"    Entrada:      {s.entry_price}")
        lines.append(f"    SL:           {s.stop_loss}")
        lines.append(f"    TP:           {s.take_profit}")
        lines.append(f"    Break Even:   {s.break_even_price}")
        lines.append(f"    Trailing:     {s.trailing_distance*100:.2f}%")
        lines.append(f"    Leverage:     {s.leverage_max}x")
        lines.append(f"    Régimen:      {s.regime}")
        lines.append(f"    Condiciones:  {', '.join(s.conditions)}")
        lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def summary_by_tier(signals: List[OmegaSignal]) -> pd.DataFrame:
    if not signals:
        return pd.DataFrame()
    df = pd.DataFrame([{'tier': s.tier, 'score': s.omega_score} for s in signals])
    return df.groupby('tier').agg(
        count=('score', 'count'),
        avg_score=('score', 'mean'),
        max_score=('score', 'max'),
    ).reset_index()


def star_trade_report(pred: StarTradePrediction) -> str:
    lines = [
        "=" * 70,
        "  🌟 STAR TRADE MONITOR — Horario Argentina (UTC-3)",
        "=" * 70,
        f"  Día: {pred.day_name}",
        f"  Ventana actual: {pred.current_window_label}",
        f"  En ventana estrella: {'✅ SÍ' if pred.is_in_window else '⏳ NO'}",
        "",
        f"  Próximo trade estrella:",
        f"    Etiqueta: {pred.next_window_label}",
        f"    Inicio:   {pred.next_window_start} ARG",
        f"    Faltan:   {pred.minutes_until_next} minutos",
        f"    Hora prevista: {pred.next_star_time} ARG",
        f"    Confianza: {pred.confidence*100:.1f}%",
        "",
        f"  Activos probables: {', '.join(pred.expected_assets)}",
        f"  Leverage recomendado: {pred.recommended_leverage}x",
        "=" * 70,
    ]
    return "\n".join(lines)