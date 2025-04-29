<template>
  <div class="container">
    <h1 class="text-center page-title mt-4">SMHI Weather Data Visualization</h1>
    
    <div v-if="error" class="alert alert-danger">
      {{ error }}
    </div>
    
    <div class="row">
      <div class="col-md-4">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">Search for a City</h5>
            <CitySearch @city-selected="handleCitySelect" />
            
            <div v-if="selectedCity" class="mt-3">
              <h6>Selected City: {{ selectedCity.name }}</h6>
              <div class="mt-2">
                <button 
                  class="btn btn-sm btn-outline-primary me-2" 
                  :class="{'btn-primary text-white': !showHistorical && !showMonthly}" 
                  @click="toggleDataType('recent')"
                >
                  Recent Data
                </button>
                <button 
                  class="btn btn-sm btn-outline-primary me-2" 
                  :class="{'btn-primary text-white': showMonthly}" 
                  @click="toggleDataType('monthly')"
                >
                  Monthly Data
                </button>
                <button 
                  class="btn btn-sm btn-outline-primary" 
                  :class="{'btn-primary text-white': showHistorical}" 
                  @click="toggleDataType('historical')"
                >
                  Historical Data
                </button>
              </div>
              <button class="btn btn-sm btn-outline-secondary mt-2" @click="goBackToAllCities">
                Back to All Cities
              </button>
            </div>
          </div>
        </div>
        
        <div class="card mt-3">
          <div class="card-body">
            <h5 class="card-title">Major Swedish Cities</h5>
            <div>
              <button 
                v-for="city in Object.keys(MAJOR_CITIES)" 
                :key="city"
                @click="selectMajorCity(city)"
                class="btn btn-sm city-badge"
                :class="selectedCity && selectedCity.name === city ? 'btn-primary' : 'btn-outline-primary'"
              >
                {{ city }}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div class="col-md-8">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">
              {{ chartTitle }}
            </h5>
            
            <div v-if="loading" class="loader">
              <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
              </div>
            </div>
            
            <TemperatureChart 
              v-else-if="chartData" 
              :data="chartData"
              :title="chartTitle"
            />
            
            <div v-else class="alert alert-info">
              Select a city to see temperature data
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, computed, onMounted } from 'vue';
import axios from 'axios';
import TemperatureChart from './components/TemperatureChart.vue';
import CitySearch from './components/CitySearch.vue';

// Major Swedish cities and their station IDs (copied from backend)
const MAJOR_CITIES = {
  "Stockholm": 97400,
  "Göteborg": 72420,
  "Malmö": 53430,
  "Uppsala": 97510,
  "Umeå": 140480,
};

export default defineComponent({
  name: 'App',
  components: {
    TemperatureChart,
    CitySearch
  },
  setup() {
    const chartData = ref(null);
    const loading = ref(true);
    const error = ref('');
    const selectedCity = ref(null);
    const showHistorical = ref(false);
    const showMonthly = ref(false);
    
    const chartTitle = computed(() => {
      if (selectedCity.value) {
        let title = `Temperature Data for ${selectedCity.value.name}`;
        if (showHistorical.value) {
          title += ' (Historical)';
        } else if (showMonthly.value) {
          title += ' (Monthly)';
        } else {
          title += ' (Recent)';
        }
        return title;
      }
      return 'Temperature Data for Major Swedish Cities';
    });
    
    // Fetch data for all major cities
    const fetchAllCitiesData = async () => {
      try {
        loading.value = true;
        error.value = '';
        selectedCity.value = null;
        showHistorical.value = false;
        showMonthly.value = false;
        
        console.log('Fetching data from:', '/api/graph/cities');
        const response = await axios.get('/api/graph/cities');
        console.log('Response received:', response.status);
        chartData.value = response.data;
        
      } catch (err) {
        console.error('Error fetching temperature data:', err.message);
        if (err.response) {
          console.error('Response data:', err.response.data);
          console.error('Response status:', err.response.status);
        }
        error.value = 'Failed to load temperature data. Please try again later.';
      } finally {
        loading.value = false;
      }
    };
    
    // Fetch data for a specific city
    const fetchCityData = async (cityName, dataType = 'recent') => {
      try {
        loading.value = true;
        error.value = '';
        
        let endpoint;
        if (dataType === 'historical') {
          endpoint = `/api/graph/historical/${cityName}`;
        } else if (dataType === 'monthly') {
          endpoint = `/api/graph/monthly/${cityName}`;
        } else {
          endpoint = `/api/graph/city/${cityName}`;
        }
          
        console.log('Fetching data from:', endpoint);
        const response = await axios.get(endpoint);
        console.log('Response received:', response.status);
        chartData.value = response.data;
        
        // Update the city info if it was found through search
        if (response.data.station_name && selectedCity.value) {
          selectedCity.value.station_name = response.data.station_name;
          selectedCity.value.station_id = response.data.station_id;
        }
      } catch (err) {
        console.error(`Error fetching data for ${cityName}:`, err.message);
        if (err.response) {
          console.error('Response data:', err.response.data);
          console.error('Response status:', err.response.status);
          
          if (err.response.status === 404) {
            error.value = err.response.data.detail || `No data found for ${cityName}`;
          } else {
            error.value = `Failed to load data for ${cityName}. Please try again.`;
          }
        } else {
          error.value = `Failed to load data for ${cityName}. Please try again.`;
        }
        chartData.value = null;
      } finally {
        loading.value = false;
      }
    };
    
    const handleCitySelect = (city) => {
      selectedCity.value = city;
      const dataType = showHistorical.value ? 'historical' : (showMonthly.value ? 'monthly' : 'recent');
      fetchCityData(city.name, dataType);
    };
    
    const selectMajorCity = (cityName) => {
      selectedCity.value = {
        id: MAJOR_CITIES[cityName],
        name: cityName
      };
      const dataType = showHistorical.value ? 'historical' : (showMonthly.value ? 'monthly' : 'recent');
      fetchCityData(cityName, dataType);
    };
    
    const toggleDataType = (dataType) => {
      if (selectedCity.value) {
        const wasHistorical = showHistorical.value;
        const wasMonthly = showMonthly.value;
        
        showHistorical.value = dataType === 'historical';
        showMonthly.value = dataType === 'monthly';
        
        if (wasHistorical !== showHistorical.value || wasMonthly !== showMonthly.value) {
          fetchCityData(selectedCity.value.name, dataType);
        }
      }
    };
    
    const toggleHistorical = (value) => {
      toggleDataType(value ? 'historical' : 'recent');
    };
    
    const goBackToAllCities = () => {
      selectedCity.value = null;
      showHistorical.value = false;
      showMonthly.value = false;
      fetchAllCitiesData();
    };
    
    // Load all cities data on component mount
    onMounted(() => {
      fetchAllCitiesData();
    });
    
    return {
      chartData,
      loading,
      error,
      selectedCity,
      showHistorical,
      showMonthly,
      chartTitle,
      handleCitySelect,
      selectMajorCity,
      toggleHistorical,
      toggleDataType,
      goBackToAllCities,
      MAJOR_CITIES
    };
  }
});
</script> 