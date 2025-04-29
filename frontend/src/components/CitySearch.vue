<template>
  <div class="search-container">
    <div class="input-group mb-3">
      <input 
        type="text" 
        class="form-control" 
        placeholder="Search for a city..." 
        v-model="searchTerm"
        @keyup.enter="searchCity"
        :disabled="loading"
      >
      <button 
        class="btn btn-primary" 
        type="button" 
        @click="searchCity"
        :disabled="loading"
      >
        <span v-if="loading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        <span v-else>Search</span>
      </button>
    </div>
    
    <div v-if="error" class="alert alert-danger">
      {{ error }}
    </div>
    
    <div v-if="results.length > 0" class="list-group mt-3">
      <button 
        v-for="city in results" 
        :key="city.id"
        type="button" 
        class="list-group-item list-group-item-action"
        @click="selectCity(city)"
      >
        {{ city.name }}
        <small class="d-block text-muted">
          ID: {{ city.id }}, Coordinates: {{ city.latitude.toFixed(2) }}, {{ city.longitude.toFixed(2) }}
        </small>
      </button>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref } from 'vue';
import axios from 'axios';

export default defineComponent({
  name: 'CitySearch',
  emits: ['city-selected'],
  setup(props, { emit }) {
    const searchTerm = ref('');
    const results = ref([]);
    const loading = ref(false);
    const error = ref('');

    const searchCity = async () => {
      if (!searchTerm.value || searchTerm.value.length < 2) {
        error.value = 'Please enter at least 2 characters';
        return;
      }

      try {
        loading.value = true;
        error.value = '';
        
        const apiUrl = `${window.location.origin}/api/cities/search/${searchTerm.value}`;
        console.log('Searching for city at:', apiUrl);
        const response = await axios.get(apiUrl);
        console.log('Search results received:', response.status);
        results.value = response.data;
        
        if (response.data.length === 0) {
          error.value = 'No matching cities found';
        }
        
      } catch (err) {
        console.error('Error searching for cities:', err.message);
        if (err.response) {
          console.error('Response data:', err.response.data);
          console.error('Response status:', err.response.status);
        }
        error.value = 'Error searching for cities. Please try again.';
      } finally {
        loading.value = false;
      }
    };

    const selectCity = (city) => {
      emit('city-selected', city);
      results.value = [];
    };

    return {
      searchTerm,
      results,
      loading,
      error,
      searchCity,
      selectCity
    };
  }
});
</script> 