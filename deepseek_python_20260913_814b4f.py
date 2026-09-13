# streamlit_app.py
import streamlit as st
import pandas as pd
from datetime import datetime

from config import PROJECT_NAME, VERSION, SYMBOLS, ENABLE_LIVE, DEMO_MODE, TZ_ARGENTINA
from main import run_scan
from report_generator import to_dataframe, summary_by_tier, star_trade_report
from star_trade_predictor import StarTradePredictor
from omega_regime_detector import OmegaRegimeDetector
from data_engine import DataEngine

st.set_page_config(page_title=PROJECT_NAME, page_icon="Ω", layout="wide")
st.title(f"Ω {PROJECT_NAME} v{VERSION}")
st.caption(f"Modo: {'🔸 DEMO' if DEMO_MODE else '🔴 LIVE'} · ENABLE_LIVE={ENABLE_LIVE} · TZ Argentina (UTC-3)")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    st.caption(f"Activos: {len(SYMBOLS)}")
    st.caption(f"TF: 5m / 15m / 1h")
    st.caption(f"Modo: {'🔸 DEMO' if DEMO_MODE else '🔴 LIVE'}")
    st.caption(f"Ahora: {datetime.now(TZ_ARGENTINA).strftime('%H:%M:%S')} ARG")

    if st.button("🔄 Escanear señales", type="primary", use_container_width=True):
        st.session_state.scan = True

    if st.button("🌟 Actualizar Star Monitor", use_container_width=True):
        st.session_state.update_star = True

    st.caption(f"Último scan: {st.session_state.get('last_scan', 'Nunca')}")

# Tabs
tab_star, tab_regime, tab_scanner, tab_omega = st.tabs([
    "🌟 Star Trade Monitor", "🌊 Ω-Regime", "📡 Scanner", "🏆 Ranking Omega"
])

# ------------------------------------------------------------
# TAB 1: STAR TRADE MONITOR
# ------------------------------------------------------------
with tab_star:
    st.subheader("🌟 Monitor de Trades Estrella — Horario Argentina (UTC-3)")
    st.caption("Ventanas óptimas de operación según backtest 2024-2026")

    predictor = StarTradePredictor()
    regime = st.session_state.get('current_regime', 'Chop')
    pred = predictor.predict(current_regime=regime)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Día", pred.day_name)
    c2.metric("Ventana actual", pred.current_window_label)
    c3.metric("Próximo estrella", f"{pred.next_star_time} ARG")
    c4.metric("Faltan", f"{pred.minutes_until_next} min")

    if pred.is_in_window:
        st.success(f"✅ **VENTANA ACTIVA** — {pred.current_window_label}")
    else:
        st.info(f"⏳ **Esperando** — Próximo trade estrella en {pred.minutes_until_next} min "
                f"({pred.next_star_time} ARG)")

    st.markdown("---")
    st.markdown("### 📊 Ventanas del día (ARG)")
    for w in predictor.windows:
        st.caption(
            f"{w['label']} · "
            f"{w['start'][0]:02d}:{w['start'][1]:02d} – {w['end'][0]:02d}:{w['end'][1]:02d} · "
            f"WR {w['wr']*100:.1f}% · PF {w['pf']} · {w['lev']}x"
        )

    st.markdown("---")
    st.markdown("### 🎯 Activos probables")
    st.write(", ".join(pred.expected_assets))
    st.markdown(f"**Leverage recomendado:** {pred.recommended_leverage}x")
    st.markdown(f"**Confianza:** {pred.confidence*100:.1f}%")

# ------------------------------------------------------------
# TAB 2: OMEGA REGIME
# ------------------------------------------------------------
with tab_regime:
    st.subheader("🌊 Monitor de Régimen Ω")

    if st.button("🔍 Analizar régimen actual", type="primary", key="regime_btn"):
        with st.spinner("Detectando régimen..."):
            de = DataEngine()
            btc = de.fetch_ohlcv('BTC/USDT', '1h', limit=500)
            if btc is not None:
                detector = OmegaRegimeDetector()
                report = detector.generate_regime_report({'1h': btc})
                st.session_state.regime_report = report
                st.session_state.current_regime = report['current_regime']

    report = st.session_state.get('regime_report')
    if report:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Régimen", report['current_regime'])
        c2.metric("Prob Ω (7d)", f"{report['probability_7d']*100:.1f}%")
        c3.metric("Prob Ω (30d)", f"{report['probability_30d']*100:.1f}%")
        c4.metric("Días Ω esperados", f"{report['expected_days']:.1f}")
        st.info(f"**Recomendación:** {report['recommendation']}")
        st.caption(f"**Fase:** {report['phase']}")
        st.caption(f"**Mejores activos:** {', '.join(report['best_assets'])}")
        st.caption(f"**Mejores horas UTC:** {report['best_hours']}")
    else:
        st.info("Presioná 'Analizar régimen actual' para ver el estado.")

# ------------------------------------------------------------
# TAB 3: SCANNER
# ------------------------------------------------------------
with tab_scanner:
    st.subheader("📡 Scanner de activos")

    if st.session_state.get('scan') or 'omega_signals' not in st.session_state:
        with st.spinner("🔍 Escaneando activos y rankeando..."):
            try:
                signals = run_scan()
                st.session_state.omega_signals = signals
                st.session_state.last_scan = datetime.now(TZ_ARGENTINA).strftime("%H:%M:%S")
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.omega_signals = []
        st.session_state.scan = False

    signals = st.session_state.get('omega_signals', [])
    if not signals:
        st.info("Presioná 'Escanear señales' en la sidebar.")
    else:
        st.success(f"✅ {len(signals)} señales encontradas")
        df = to_dataframe(signals)
        st.dataframe(df, use_container_width=True, height=600)

# ------------------------------------------------------------
# TAB 4: RANKING OMEGA
# ------------------------------------------------------------
with tab_omega:
    st.subheader("🏆 Ranking Omega detallado")

    signals = st.session_state.get('omega_signals', [])
    if not signals:
        st.info("Presioná 'Escanear señales' primero.")
    else:
        st.markdown("### 📊 Resumen por Tier")
        st.dataframe(summary_by_tier(signals), use_container_width=True)

        st.markdown("### 🎯 Top señales")
        for s in signals[:5]:
            with st.expander(f"{s.symbol} — {s.direction} — Ω Score: {s.omega_score:.2f} [{s.tier}]"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Ω Score", f"{s.omega_score:.2f}")
                c1.metric("WR estimado", f"{s.estimated_wr*100:.1f}%")
                c1.metric("PF estimado", f"{s.estimated_pf:.2f}")
                c2.metric("Entrada", f"{s.entry_price}")
                c2.metric("Stop Loss", f"{s.stop_loss}")
                c2.metric("Take Profit", f"{s.take_profit}")
                c3.metric("Break Even", f"{s.break_even_price}")
                c3.metric("Trailing", f"{s.trailing_distance*100:.2f}%")
                c3.metric("Leverage", f"{s.leverage_max}x")
                st.caption(f"Régimen: {s.regime} · Condiciones: {', '.join(s.conditions)}")

st.markdown("---")
st.caption(
    f"Última actualización: {st.session_state.get('last_scan', 'Nunca')} · "
    f"D.A.P.S-SIGNALS Ω v{VERSION}"
)