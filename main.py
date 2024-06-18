import requests
import pandas as pd
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

# Wczytywanie danych stacji monitorujących
df = pd.read_csv('monitoring_stations_PL.csv')

# Zdefiniowanie zakresów AQI
aqi_ranges = {
    'PM10': [(0, 20, 'Very Good'), (20.1, 50, 'Good'), (50.1, 80, 'Moderate'), (80.1, 110, 'Passable'),
             (110.1, 150, 'Bad'), (150.1, 1000, 'Very Bad')],
    'PM2.5': [(0, 13, 'Very Good'), (13.1, 35, 'Good'), (35.1, 55, 'Moderate'), (55.1, 75, 'Passable'),
              (75.1, 110, 'Bad'), (110.1, 1000, 'Very Bad')],
    'O3': [(0, 70, 'Very Good'), (70.1, 120, 'Good'), (120.1, 150, 'Moderate'), (150.1, 180, 'Passable'),
           (180.1, 240, 'Bad'), (240.1, 1000, 'Very Bad')],
    'NO2': [(0, 40, 'Very Good'), (40.1, 100, 'Good'), (100.1, 150, 'Moderate'), (150.1, 230, 'Passable'),
            (230.1, 400, 'Bad'), (400.1, 1500, 'Very Bad')],
    'SO2': [(0, 50, 'Very Good'), (50.1, 100, 'Good'), (100.1, 200, 'Moderate'), (200.1, 350, 'Passable'),
            (350.1, 500, 'Bad'), (500.1, 2000, 'Very Bad')]
}


def get_air_quality_data(station):
    '''The function collects all sensors installed at chosen monitoring station
       and then gets most recent measurements from all sensors.
       In addition, based on fixed criteria it assigns AQI category to all pollutants (sensors).'''

    sensors = df[df['station_name'] == station]['sensor_id'].tolist()
    all_data = []

    for sensor_id in sensors:
        api_endpoint = f'https://api.gios.gov.pl/pjp-api/rest/data/getData/{sensor_id}'
        response = requests.get(api_endpoint)

        if response.status_code == 200:
            values = response.json().get('values')
            if values:
                sensor_data = None
                for v in values:
                    if v.get('value') is not None:
                        sensor_data = v
                        break

                if sensor_data is None:
                    continue

                pollutant = response.json().get('key')
                if pollutant is None:
                    continue

                aqi_value = sensor_data.get('value')
                if aqi_value is None:
                    continue

                aqi_category = get_aqi_category(pollutant, aqi_value)
                all_data.append(
                    {'sensor_id': sensor_id, 'key': pollutant, 'value': sensor_data, 'aqi_category': aqi_category}
                )
            else:
                print(f"No values found for sensor ID {sensor_id}")
        else:
            print(
                f"Error while collecting data from API for sensor ID {sensor_id}. Status code: {response.status_code}")
            return html.Div(
                f'Error while collecting data from API for sensor ID {sensor_id}. Check internet connection.')

    return all_data


def get_aqi_category(pollutant, value):
    '''This function assigns AQI category to the sensor (pollutant) based on most recent measurement
    according to fixed criteria'''

    ranges = aqi_ranges.get(pollutant, [])
    aqi_category = "Not included in AQI index"

    for range_tuple in ranges:
        if range_tuple[0] <= value <= range_tuple[1]:
            aqi_category = range_tuple[2]
            break

    return aqi_category


# Creating dash app
app = dash.Dash(__name__)
server = app.server
app.layout = html.Div([
    html.Label('Choose monitoring station:'),
    dcc.Dropdown(
        id='station-dropdown',
        options=[{'label': station, 'value': station} for station in df['station_name'].unique()],
        value=df['station_name'].unique()[0],  # First station is set as default value
        style={'width': '50%'}
    ),
    html.Br(),
    html.Div(id='output-container'),
])


@app.callback(
    Output('output-container', 'children'),
    [Input('station-dropdown', 'value')]
)
def update_output(station):
    if station is None:
        return html.Div('Choose monitoring station.')

    station_data = get_air_quality_data(station)

    # Creating HTML table
    table_header = [
        html.Th("Sensor ID", style={'text-align': 'left', 'width': '20%'}),
        html.Th("Pollutant", style={'text-align': 'left', 'width': '20%'}),
        html.Th("Most recent measurement", style={'text-align': 'left', 'width': '35%'}),
        html.Th("AQI Category", style={'text-align': 'left', 'width': '25%'})
    ]
    table_rows = []

    for sensor_data in station_data:
        sensor_id = sensor_data['sensor_id']
        key = sensor_data['key']
        data_value = sensor_data['value']
        aqi_category = sensor_data['aqi_category']

        # setting background color based on AQI category
        if aqi_category == 'Very Good':
            background_color = 'green'
            text_color = 'white'
        elif aqi_category == 'Good':
            background_color = 'lightgreen'
            text_color = 'black'
        elif aqi_category == 'Moderate':
            background_color = 'yellow'
            text_color = 'black'
        elif aqi_category == 'Passable':
            background_color = 'orange'
            text_color = 'black'
        elif aqi_category == 'Bad':
            background_color = 'red'
            text_color = 'white'
        elif aqi_category == 'Very Bad':
            background_color = 'darkred'
            text_color = 'white'
        else:
            background_color = 'white'
            text_color = 'black'

        # Joining date and measurement into one string
        data_str = f"{data_value['date']}: {data_value['value']:.2f}"

        table_row = html.Tr([
            html.Td(sensor_id, style={'text-align': 'left', 'width': '20%'}),
            html.Td(key, style={'text-align': 'left', 'width': '20%'}),
            html.Td(data_str, style={'text-align': 'left', 'width': '35%'}),
            html.Td(aqi_category, style={'text-align': 'left', 'background-color': background_color,
                                         'color': text_color, 'width': '25%'})
        ])
        table_rows.append(table_row)

    return html.Table(
        [html.Thead(table_header), html.Tbody(table_rows)],
        style={'width': '100%', 'border-collapse': 'collapse'}
    )


if __name__ == '__main__':
    app.run_server(debug=False)

