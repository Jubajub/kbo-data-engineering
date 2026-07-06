import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pymongo import MongoClient

# -----------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & DESIGN CORPORATE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Hôtellerie - KBO",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Palette de couleurs professionnelles
COLOR_PRIMARY = "#1E3A8A"     # Bleu Marine
COLOR_SECONDARY = "#475569"   # Gris Ardoise
COLOR_ACCENT = "#0EA5E9"      # Bleu Clair (Accent)
COLOR_PROFIT = "#10B981"      # Vert (Positif)
COLOR_LOSS = "#EF4444"        # Rouge (Négatif)

# -----------------------------------------------------------------------------
# 2. EXTRACTION DES DONNÉES
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    uri = "mongodb://admin:password123@localhost:27017/"
    client = MongoClient(uri)
    db = client["kbo_database"]
    cursor = db["enterprise_gold"].find({}, {"_id": 0})
    df = pd.DataFrame(list(cursor))
    return df

with st.spinner("Synchronisation avec le Data Lake..."):
    df = load_data()

if df.empty:
    st.error("Aucune donnée disponible. Vérifiez le pipeline du Jour 3.")
    st.stop()

# -----------------------------------------------------------------------------
# 3. BARRE LATÉRALE (FILTRES)
# -----------------------------------------------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png", width=50)
st.sidebar.title("Paramètres d'Analyse")
st.sidebar.markdown("---")

annees_disponibles = sorted(df["Year"].unique(), reverse=True)
annees_selectionnees = st.sidebar.multiselect("🗓️ Exercice Comptable", options=annees_disponibles, default=annees_disponibles)

ca_min, ca_max = float(df["ChiffreAffaires"].min()), float(df["ChiffreAffaires"].max())
ca_range = st.sidebar.slider("💶 Chiffre d'Affaires (€)", min_value=ca_min, max_value=ca_max, value=(ca_min, ca_max))

df_filtered = df[
    (df["Year"].isin(annees_selectionnees)) & 
    (df["ChiffreAffaires"] >= ca_range[0]) & 
    (df["ChiffreAffaires"] <= ca_range[1])
]

# -----------------------------------------------------------------------------
# 4. EN-TÊTE ET KPIs
# -----------------------------------------------------------------------------
st.title("📊 Analyse Financière - Secteur Hôtelier")
st.markdown(f"**Données consolidées depuis HDFS** | Période analysée : {min(annees_selectionnees) if annees_selectionnees else '-'} à {max(annees_selectionnees) if annees_selectionnees else '-'}")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Entreprises", f"{df_filtered['EnterpriseNumber'].nunique():,}".replace(",", " "))
with col2:
    st.metric("CA Moyen Sectoriel", f"{df_filtered['ChiffreAffaires'].mean():,.0f} €".replace(",", " "))
with col3:
    st.metric("Marge Nette Moyenne", f"{df_filtered['MargeNette_percent'].mean():.2f} %")
with col4:
    st.metric("Ratio Liquidité Moyen", f"{df_filtered['LiquiditeReduite_ratio'].mean():.2f}")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. VISUALISATIONS AVANCÉES
# -----------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 Évolution du Chiffre d'Affaires")
    df_trend = df_filtered.groupby("Year").agg({"ChiffreAffaires": "sum", "ResultatNet": "sum"}).reset_index()
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(x=df_trend["Year"], y=df_trend["ChiffreAffaires"], name="CA Total", marker_color=COLOR_PRIMARY))
    fig_trend.add_trace(go.Scatter(x=df_trend["Year"], y=df_trend["ResultatNet"], name="Résultat Net", mode='lines+markers', line=dict(color=COLOR_ACCENT, width=3)))
    
    fig_trend.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(tickmode='linear', dtick=1, showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with col_right:
    st.subheader("🎯 Matrice de Santé Financière")
    fig_scatter = px.scatter(
        df_filtered, 
        x="MargeNette_percent", 
        y="ROE_percent", 
        size="ChiffreAffaires", 
        color="LiquiditeReduite_ratio",
        color_continuous_scale="Blues",
        hover_name="EnterpriseNumber",
        labels={"MargeNette_percent": "Marge Nette (%)", "ROE_percent": "ROE (%)", "LiquiditeReduite_ratio": "Liquidité"}
    )
    fig_scatter.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0", zeroline=True, zerolinecolor=COLOR_SECONDARY),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0", zeroline=True, zerolinecolor=COLOR_SECONDARY),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. CLASSEMENTS ET DONNÉES BRUTES
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🏆 Top 10 - Les plus rentables (Par Résultat Net)")

top_10 = df_filtered.sort_values(by="ResultatNet", ascending=False).head(10)
# Formatage pour un affichage propre
top_10_display = top_10[["EnterpriseNumber", "Year", "ChiffreAffaires", "ResultatNet", "MargeNette_percent"]].copy()
top_10_display["ChiffreAffaires"] = top_10_display["ChiffreAffaires"].apply(lambda x: f"{x:,.0f} €".replace(",", " "))
top_10_display["ResultatNet"] = top_10_display["ResultatNet"].apply(lambda x: f"{x:,.0f} €".replace(",", " "))
top_10_display["MargeNette_percent"] = top_10_display["MargeNette_percent"].apply(lambda x: f"{x:.2f} %")

st.dataframe(top_10_display, use_container_width=True, hide_index=True)

with st.expander("📂 Explorer la base de données brute (Couche Gold)"):
    st.dataframe(df_filtered.sort_values(by=["Year", "ChiffreAffaires"], ascending=[False, False]), use_container_width=True, hide_index=True)