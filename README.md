# SMHI Weather Data Visualization

This project displays temperature data from the Swedish Meteorological and Hydrological Institute (SMHI) API. It allows users to view temperature trends for major Swedish cities and search for specific locations.

## Features

- View temperature data for major Swedish cities (Stockholm, Göteborg, Malmö, Uppsala, Umeå)
- Search for specific cities and view their temperature data
- Display average temperature across cities
- Visualize temperature trends with interactive charts

## Project Structure

The project is divided into two main parts:

- **Backend**: FastAPI application that fetches and processes data from the SMHI API
- **Frontend**: React application that displays the data in an interactive UI

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm or yarn

### Installation

1. Clone the repository

2. Set up the backend:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

3. Set up the frontend:
```bash
cd frontend
npm install
npm start
```

4. Open your browser and navigate to `http://localhost:3000` to use the application.

## API Endpoints

- `/cities` - Get temperature data for all major Swedish cities
- `/city/{city_name}` - Get temperature data for a specific city
- `/search-city/{query}` - Search for cities by name

## Technologies Used

### Backend
- FastAPI
- Pandas
- Requests

### Frontend
- React
- Chart.js
- Axios
- Bootstrap

## Data Source

All weather data is sourced from the SMHI Open Data API: https://opendata.smhi.se/

## License

This project is open source and available under the MIT License.
