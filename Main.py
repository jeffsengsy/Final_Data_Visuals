import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from datetime import datetime
import plotly.express as px
from sodapy import Socrata


# Import the community data files.
df_communities = pd.read_csv("communities.csv")

# Ensure all community names are strings (in case of mixed data types)
df_communities['Community'] = df_communities['Community'].astype(str)

# API access
# Website: https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2/data_preview

def call_data(start_date, end_date, crime_types, community):
    """Makes a call to the chicago crime API for multiple crime types."""
    client = Socrata("data.cityofchicago.org", None)
    
    # Create a SQL WHERE clause for multiple crimes
    crime_conditions = " OR ".join([f"primary_type = '{crime}'" for crime in crime_types])
    where_clause = f"date > '{start_date}' AND date < '{end_date}' AND ({crime_conditions}) AND community_area = '{community}'"
    
    results = client.get("ijzp-q8t2",
                         select="id, case_number, block, primary_type, description, location_description, date, community_area, fbi_code,"
                                "year, latitude, longitude",
                         where=where_clause,
                         limit=250000,
                         order="date DESC")


    return results


def crime_names():
    """Returns a list of the available crimes to choose from."""

    keep_crimes = {'Primary Type': ['THEFT', 'ASSAULT', 'SEX OFFENSE', 'BURGLARY','MOTOR VEHICLE THEFT',
                                    'OFFENSE INVOLVING CHILDREN', 'CRIMINAL TRESPASS', 'ROBBERY',
                                    'CRIMINAL SEXUAL ASSAULT', 'STALKING', 'HOMICIDE', 'KIDNAPPING',
                                    'DOMESTIC VIOLENCE']}

    df_crime_type = pd.DataFrame(keep_crimes)

    return df_crime_type


def convert_community(chosen_community, df_communities):
    """Converts the chosen community to a number that can be called in the API."""
    
    # Ensure both columns are of the same type (string)
    df_communities['Community Area'] = df_communities['Community Area'].astype(str)

    # Find the corresponding community area number
    community_row = df_communities[df_communities['Community'] == chosen_community]
    
    if community_row.empty:
        return None  # or handle appropriately if no match is found

    community_area_number = community_row.iloc[0]['Community Area']
    
    return community_area_number


@st.cache_data
def clean_crimes(crime_df, neighborhoods, crime_types, start_date="2018-01-01", end_date="2024-01-01"):
    """Combines the crime, demographic and neighborhoods dataframe into one."""

    # Convert 'Date' column to datetime
    crime_df['date'] = pd.to_datetime(crime_df['date'], format='mixed')

    # Apply filter to dataframe
    mask_1 = crime_df['date'] >= start_date
    mask_2 = crime_df['date'] < end_date

    crime_df = crime_df.loc[mask_1 & mask_2].sort_values(by='date')

    # Create columns with hour, day, month, year
    crime_df['hour'] = crime_df['date'].dt.hour
    crime_df['day'] = crime_df['date'].dt.day
    crime_df['month'] = crime_df['date'].dt.month
    crime_df['year'] = crime_df['date'].dt.year

    # Create a feature based on time of day
    conditions = [
        (crime_df['hour'] >= 0) & (crime_df['hour'] < 4),
        (crime_df['hour'] >= 4) & (crime_df['hour'] < 8),
        (crime_df['hour'] >= 8) & (crime_df['hour'] < 12),
        (crime_df['hour'] >= 12) & (crime_df['hour'] < 16),
        (crime_df['hour'] >= 16) & (crime_df['hour'] < 20),
        (crime_df['hour'] >= 20)
    ]

    values = ['12am to 4am', '4am to 8am', '8am to 12pm', '12pm to 4pm', '4pm to 8pm', '8pm to 12am']

    # Add a default value (e.g., "Unknown") in case no condition is met
    crime_df['Time of Day'] = np.select(conditions, values, default="Unknown")

    # Filter for only the crimes of interest
    crime_df = crime_df.loc[crime_df['primary_type'].isin(crime_types)]

    # Rename the column Community in the Communities dataframe
    neighborhoods = neighborhoods.rename(columns={"Community Area": "community_area"})

    # Make the community_area a string in neighborhoods
    neighborhoods['community_area'] = neighborhoods['community_area'].astype(str)

    # Add the communities to the dataframe
    crime_df_1 = pd.merge(crime_df, neighborhoods, on='community_area', how='outer')

    # Remove NA columns where id = NaN. This is from the discrepancy between the current date and the
    # chosen end date.
    crime_df_2 = crime_df_1.dropna(subset="id")

    # Obtain the total number of crimes
    crime_total = len(crime_df_2)

    return crime_df_2, crime_total


def plot_community_time_day(df):
    """Determines and plots the number of crimes in the community by the time of day."""

    # Order for the x_axis
    order = ['12am to 4am', '4am to 8am', '8am to 12pm', '12pm to 4pm', '4pm to 8pm', '8pm to 12am']

    # Plot the crimes by time of day
    fig = px.histogram(df, x='Time of Day', category_orders={'Time of Day': order})
    # Set the pie chart size.
    fig.update_layout(width=400, height=350)

    return fig


def location_description(df):
    """Plots a histogram of the location of most likely occurrence."""

    value_counts = df['location_description'].value_counts()

    # Does a breakdown of occurrence for each crime.
    fig = px.pie(df, values=value_counts.values, names=value_counts.index)
    fig.update_layout(width=450, height=400)
    # Removes the labels
    fig.update_traces(textposition='inside', textinfo='none')

    return fig

def crime_map(df):
    """Plots a color-coded map of different crime locations and adds a legend."""
    # Generate a unique color for each crime type
    unique_crimes = df['primary_type'].unique()
    colors = px.colors.qualitative.Safe  # Use a predefined qualitative color scale
    crime_colors = {crime: colors[i % len(colors)] for i, crime in enumerate(unique_crimes)}

    # Create a column for color based on crime type
    df['color'] = df['primary_type'].map(crime_colors)

    # Prepare data for map
    latitude = df['latitude'].astype(float)
    longitude = df['longitude'].astype(float)
    crime_type = df['primary_type']

    df_coordinates = pd.DataFrame({
        'latitude': latitude,
        'longitude': longitude,
        'crime_type': crime_type,
        'color': df['color']
    }).dropna()

    return df_coordinates, crime_colors

def plot_top_5_crimes(df):
    """Plots a horizontal bar chart of the top crimes in the community."""
    # Count the number of occurrences of each crime
    top_crimes = df['primary_type'].value_counts().head(5)
    
    # Create a DataFrame for plotting
    top_crimes_df = pd.DataFrame({
        'Crime Type': top_crimes.index,
        'Count': top_crimes.values
    })
    
    # Create a bar chart using Altair
    chart = alt.Chart(top_crimes_df).mark_bar(color='teal').encode(
        x=alt.X('Count', title='Number of Crimes'),
        y=alt.Y('Crime Type', sort='-x', title='Crime Type')
    ).properties(
        width=400,
        height=300,
        title="Top 5 Crimes"
    )
    
    return chart



st.set_page_config(
    page_title="Neighborhood Watch Statistics",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Chicago Neighborhood Crime") 

alt.themes.enable("dark")

# Provide initial start and end times for the date inputs.
start_init = "2023-10-01"
end_init = "2024-01-01"

# Convert to datetime.
start_init_1 = pd.to_datetime(start_init)
end_init_1 = pd.to_datetime(end_init)

# Obtain the crime names
primary_crime_names = crime_names()

# Streamlit application UI code below.
# Add a sidebar

# Sidebar updates for multiple crime types
with st.sidebar:
    st.image("chicago_flag.png", use_container_width=True)  # Add the Chicago flag
    st.title('Chicago Neighborhood Crime Dashboard')
    begin_date = st.date_input('Begin Date', start_init_1)
    ending_date = st.date_input('End Date', end_init_1)
    st.text("")
    community_chosen = st.selectbox('Community', options=df_communities['Community'].astype(str).unique())
    crime_type = st.multiselect('Crime Types (Select up to 5)', 
                                options=primary_crime_names['Primary Type'], 
                                default=['THEFT'],  # Default selection
                                max_selections=5)
    st.text("")
    data_button = st.button("Update Data")

community_chosen_1 = convert_community(community_chosen, df_communities)

# Query the current date
starting_date = "2018-01-01T00:00:00.000"
current_date = datetime.now()
end_date = current_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
end_date_2 = f"{end_date}"


# Obtain the data from the chicago crime API.
results = call_data(starting_date, end_date_2, crime_type, community_chosen_1)
df_crime_1 = pd.DataFrame.from_records(results)

# Convert the datetime to a string
begin_date_1 = begin_date.strftime('%Y-%m-%d')
ending_date_1 = ending_date.strftime('%Y-%m-%d')

# Create a placeholder for the crime count.
st.subheader(f'Total: {crime_type}')
crimecount_placeholder = st.empty()

# Placeholder for horizontal bar chart of top 5 crimes
st.subheader('Top 5 Crimes')
top_crimes_placeholder = st.empty()

# Clean the data and create the Time of Day column
new_df, crime_tot = clean_crimes(df_crime_1, df_communities, crime_type, begin_date_1, ending_date_1)

if 'new_df_key_1' not in st.session_state:
    # Add the new dataframe to the current session state
    st.session_state['new_df_key_1'] = new_df
    
    # Update the Top 5 Crimes chart
    fig = plot_top_5_crimes(st.session_state['new_df_key_1'])
    top_crimes_placeholder.altair_chart(fig)

# Count of Total Crimes and update the value
crimecount_placeholder.subheader(crime_tot)

st.text("")
st.text("")

# Rows to hold the pie and bar charts.
col1, col2 = st.columns(2)
with col1:
    # Box Plot
    st.subheader('Time of Day')
    boxplot_placeholder = st.empty()
    fig_box = plot_community_time_day(st.session_state['new_df_key_1'])
    boxplot_placeholder.plotly_chart(fig_box)

    #Pie chart
with col2:
    st.subheader('Location Description')
    piechart_placeholder = st.empty()
    fig_pie = location_description(st.session_state['new_df_key_1'])
    piechart_placeholder.plotly_chart(fig_pie)


st.text("")

# Location Map and Crime Legend
st.subheader("Crime Location Map")

df_coordinates, crime_colors = crime_map(st.session_state['new_df_key_1'])

# Create a scatter map using Plotly Express
map_fig = px.scatter_mapbox(
    df_coordinates,
    lat='latitude',
    lon='longitude',
    color='crime_type',
    color_discrete_map=crime_colors,
    hover_data=['crime_type'],
    title="Crime Locations",
    height=500,
    zoom=10
)

# Configure the map style
map_fig.update_layout(
    mapbox_style="carto-positron",
    showlegend=True,
    legend_title="Crime Type",
    margin={"r": 0, "t": 30, "l": 0, "b": 0}
)

# Display the map
st.plotly_chart(map_fig, use_container_width=True)



# Load the data and update the placeholders when "Update Data" is clicked.
if data_button:
    # Refresh data
    new_df, crime_tot = clean_crimes(df_crime_1, df_communities, crime_type, begin_date_1, ending_date_1)
    st.session_state['new_df_key_1'] = new_df

    # Update the Top 5 Crimes chart
    fig = plot_top_5_crimes(st.session_state['new_df_key_1'])
    top_crimes_placeholder.altair_chart(fig)

    # Update the other visualizations
    fig_box = plot_community_time_day(st.session_state['new_df_key_1'])
    boxplot_placeholder.plotly_chart(fig_box)

    fig_pie = location_description(st.session_state['new_df_key_1'])
    piechart_placeholder.plotly_chart(fig_pie)

    # Update the map
    df_coordinates, color, size = crime_map(st.session_state['new_df_key_1'])
    create_map.map(df_coordinates, color=color, size=size)
