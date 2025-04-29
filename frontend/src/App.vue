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
    
    const chartTitle = computed(() => {
      if (selectedCity.value) {
        return `Temperature Data for ${selectedCity.value.name}`;
      }
      return 'Temperature Data for Major Swedish Cities';
    });
    
    // Fetch data for all major cities
    const fetchAllCitiesData = async () => {
      try {
        loading.value = true;
        error.value = '';
        selectedCity.value = null;
        
        const apiUrl = `${window.location.origin}/api/graph/cities`;
        console.log('Fetching data from:', apiUrl);
        const response = await axios.get(apiUrl);
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
    const fetchCityData = async (cityName) => {
      try {
        loading.value = true;
        error.value = '';
        
        const apiUrl = `${window.location.origin}/api/graph/city/${cityName}`;
        console.log('Fetching data from:', apiUrl);
        const response = await axios.get(apiUrl);
        console.log('Response received:', response.status);
        chartData.value = response.data;
        
      } catch (err) {
        console.error(`Error fetching data for ${cityName}:`, err.message);
        if (err.response) {
          console.error('Response data:', err.response.data);
          console.error('Response status:', err.response.status);
        }
        error.value = `Failed to load data for ${cityName}. Please try again.`;
        chartData.value = null;
      } finally {
        loading.value = false;
      }
    };
    
    const handleCitySelect = (city) => {
      selectedCity.value = city;
      fetchCityData(city.name);
    };
    
    const selectMajorCity = (cityName) => {
      selectedCity.value = {
        id: MAJOR_CITIES[cityName],
        name: cityName
      };
      fetchCityData(cityName);
    };
    
    const goBackToAllCities = () => {
      selectedCity.value = null;
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
      chartTitle,
      handleCitySelect,
      selectMajorCity,
      goBackToAllCities,
      MAJOR_CITIES
    };
  }
});
</script> 