import streamlit as st
import geopandas as gpd, pandas as pd
import plotly.express as px
import plotly.graph_objects as go

dep_path = "./Interrupciones_sunass/data/dep_peru.shp"  # departamental
data_csv = "./Interrupciones_sunass/data/sunnas_int.csv"


@st.cache_data
def load_data():
    df_shp = gpd.read_file(dep_path)
    df_csv = pd.read_csv(data_csv)

    return df_shp, df_csv


def merge_data(df_shp, df_csv):
    data = pd.merge(
        df_shp, df_csv, how="right", right_on="departamento", left_on="depa"
    )
    return data


dep_peru, df_clean = load_data()
df_clean['afect_hour'] = df_clean['numconexdom'] / df_clean['hours']
df_clean['departamento'] = df_clean.departamento.str.title()

st.title("Interrupciones de servicio de agua, Peru")

# Filters
empresas = df_clean.eps.unique()
tipo_int = df_clean.tipointerrupcion.unique()
motivo_int = df_clean.motivointerrupcion.unique()
departamentos = df_clean.departamento.unique()
responsabilidad = df_clean.responsabilidad.unique()
anio = df_clean.year.unique()



# Añadir un selector para elegir el tipo de interrupción

with st.sidebar:
    selected_tipo_interrupcion = st.selectbox(
        "Tipo de interrupción:", tipo_int
    )
    selected_dep = st.multiselect("Departamentos", departamentos)
    selected_anios = st.multiselect("Años", anio)
    selected_resp = st.multiselect("Responsabilidad", responsabilidad)
    selected_motv = st.multiselect("Motivo de Interrupción", motivo_int)


def filter_data(data, column, values):
    if isinstance(values, str):
        return data.query(f'{column} == @values')
    if len(values) > 0:
        return data.query(f'{column} in @values')
    return data




def plt_historical(
    title="Comparación de interrupciones por año", ylabel = "Cantidad", 
    data = df_clean, col = 'hours'
    ):
    data = filter_data(data, "departamento", selected_dep)
    data = filter_data(data, "responsabilidad", selected_resp)
    data = filter_data(data, "motivointerrupcion", selected_motv)


    df_grouped = data.groupby(["year", "tipointerrupcion"], as_index=False).agg(
        count=(col, "sum")
    )

    # Crear el gráfico de líneas con Plotly
    fig = px.line(
        df_grouped,
        x="year",
        y="count",
        color="tipointerrupcion",
        title=title,
        labels={
            "year": "Año",
            "count": ylabel,
            "tipointerrupcion": "Tipo de interrupción",
        },
    )
    return st.plotly_chart(fig)

st.header("Series históricas")
plt_historical()
plt_historical("Camiones Sisterna Desplegados", col = 'camiones_sis')



st.header(f"Interrupciones {selected_tipo_interrupcion}s")

st.subheader("Por Departamentos")

def plt_group_metrica(
    data,
    group_col="departamento",
    title = "Duración total de las interrupciones por departamento",
    filter_years=selected_anios,
    filter_group_col=selected_dep,
    col_m_calc="hours",
    col_year="year",
    metrica="mean",
    name_bar_c = None
):

    data = filter_data(data, 'responsabilidad', selected_resp)
    data = filter_data(data, 'motivointerrupcion', selected_motv)
    data = filter_data(data, 'tipointerrupcion', selected_tipo_interrupcion)
    df_filtered = filter_data(data, 'year', filter_years)#  data[data[col_year].isin(filter_years)]

    df_grouped = df_filtered.groupby(group_col, as_index=False).agg(
        metric=(col_m_calc, metrica)
    )
    df_grouped["color"] = df_grouped[group_col].apply(
        lambda x: "red" if x in filter_group_col else "lightblue"
    )
    df_grouped = df_grouped.sort_values(by="metric", ascending=False).head(15)
    name_bar = group_col if name_bar_c is None else name_bar_c
    
    fig = go.Figure()

    for i, row in df_grouped.iterrows():
        fig.add_trace(
            go.Bar(
                x=[row["metric"]],
                y=[row[name_bar]],
                orientation="h",
                name=row[group_col],
                marker=dict(color=row["color"]),
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Total",
        yaxis_title="Departamento",
        showlegend=False,
        yaxis=dict(categoryorder="total ascending"),
        template="plotly_white",
    )

    # Mostrar el gráfico en Streamlit
    return st.plotly_chart(fig)

c11, c12 = st.columns(2)

with c11: plt_group_metrica(df_clean, title = "Total de Interrupciones",  metrica="sum")
with c12: plt_group_metrica(df_clean, title = "Promedio de conexiones afectadas",  metrica="mean", col_m_calc = "numconexdom")

st.subheader("Por Empresa Prestadora de Servicio")

c21, c22 = st.columns(2)
with c22: plt_group_metrica(df_clean, 'eps', title = "Número total de Interrupciones", filter_group_col=["lima"], metrica="sum")
with c21: plt_group_metrica(df_clean, 'eps', title = "Número promedio de conexiones afectadas", filter_group_col=["lima"], metrica="mean", col_m_calc = "numconexdom", name_bar_c = "eps")

st.subheader("Provincias más afectadas | Con mayor recurrencia")

# Crear una nueva columna 'prov_dep'
df_clean["prov_dep"] = df_clean["provincia"] + " - " + df_clean["departamento"]

# Filtrar los datos donde 'hours' > 0
df_filtered = df_clean[df_clean["hours"] > 0]

# Agrupar por 'prov_dep' y calcular la duración total media

def plt_group_metrica_prov(
    data, 
    col_name = 'hours',
    title = "",
    xlabel = "",
    metric = 'mean',
    filter_group_col = selected_dep
    ):

    data = filter_data(data, 'responsabilidad', selected_resp)
    data = filter_data(data, 'motivointerrupcion', selected_motv)
    data = filter_data(data, 'tipointerrupcion', selected_tipo_interrupcion)
    data = filter_data(data, 'year', selected_anios)#  data[data[col_year].isin(filter_years)]


    if len(filter_group_col) > 0:
        data = data.query("departamento in @filter_group_col")

    df_grouped = data.groupby(['departamento', 'provincia'], as_index=False).agg(
        metrica=(col_name, metric)
    )
    df_grouped['name'] = df_grouped["provincia"] + " - " + df_grouped["departamento"]
    df_grouped["color"] = "lightblue"
    df_top = df_grouped.sort_values(by='metrica', ascending=False).query('metrica > 0').head(10)

    fig = go.Figure()

    for i, row in df_top.iterrows():
        fig.add_trace(
            go.Bar(
                x=[row['metrica']],
                y=[row['name']],
                orientation="h",
                name=row['departamento'],
                marker=dict(color=row["color"]),
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title=xlabel,
        showlegend=False,
        yaxis=dict(categoryorder="total ascending"),
        template= 'plotly_white'
    )
    return st.plotly_chart(fig)

c31, c32 = st.columns(2)

with c31:  plt_group_metrica_prov(df_filtered,title = "Horas promedio", xlabel ="Total Horas (H)")
with c32: plt_group_metrica_prov(df_filtered, title = "Conexiones afectadas", xlabel ="Conexiones", col_name = 'numconexdom', metric = "sum")


#############
data = df_clean.copy()
data = filter_data(data, 'responsabilidad', selected_resp)
# data = filter_data(data, 'motivointerrupcion', selected_motv)
data = filter_data(data, 'tipointerrupcion', selected_tipo_interrupcion)
df_selected = filter_data(data, 'year', selected_anios)
df_selected = filter_data(data, 'departamento', selected_dep)
# df_selected = df_clean[df_clean["tipointerrupcion"] == selected_tipo_interrupcion]

df_grouped = (
    df_selected.groupby(["tipointerrupcion", "motivointerrupcion", "responsabilidad"])
    .size()
    .reset_index(name="n")
)

df_hours = df_selected.groupby(["tipointerrupcion", "motivointerrupcion", "responsabilidad"]).agg(
        metrica=('hours', 'mean')
    ).reset_index()
df_affected = df_selected.groupby(["tipointerrupcion", "motivointerrupcion", "responsabilidad"]).agg(
        metrica=('numconexdom', 'mean')
    ).reset_index()



def plot_motv_int(data = df_grouped, col_plot = 'n', title = 'Motivo de Interrupción', xlabel = "Conteo"):


    #data["motivointerrupcion"] = data["motivointerrupcion"].astype(str)
    data = data.sort_values(by=col_plot, ascending=False)

    data['color'] = data['responsabilidad'].apply(
            lambda x: "skyblue" if x == "Empresa" else ("yellow" if x == "Otros" else "green")
        )

    # # Crear el gráfico de barras con Plotly
    fig = go.Figure()
    for i, row in data.iterrows():
        fig.add_trace(
            go.Bar(
                x=[row[col_plot]],
                y=[row['motivointerrupcion']],
                orientation="h",
                name=row['responsabilidad'],
                marker=dict(color=row["color"]),
            )
        )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_title=xlabel,
        showlegend=False,
        title= title,
        yaxis_title="Motivo de la interrupción",
    )

    # Mostrar el gráfico en Streamlit
    return st.plotly_chart(fig)


st.subheader("Motivo de interrupción")
plot_motv_int()
plot_motv_int(df_hours, 'metrica', xlabel = "Total Horas", title = "Horas promedio por tipo de interrupcion")




