<template>
  <div class="chart-container">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script>
import { Chart, registerables } from 'chart.js';
import { defineComponent, onMounted, watch, ref } from 'vue';

Chart.register(...registerables);

// City colors for consistent display
const CITY_COLORS = {
  'Stockholm': 'rgb(54, 162, 235)',
  'Göteborg': 'rgb(255, 99, 132)',
  'Malmö': 'rgb(75, 192, 192)',
  'Uppsala': 'rgb(255, 159, 64)',
  'Umeå': 'rgb(153, 102, 255)',
  'Average': 'rgb(0, 0, 0)'
};

export default defineComponent({
  name: 'TemperatureChart',
  props: {
    data: {
      type: Object,
      required: true
    },
    title: {
      type: String,
      default: 'Temperature Data'
    }
  },
  setup(props) {
    const chartCanvas = ref(null);
    let chart = null;

    const getCityColor = (cityName) => {
      return CITY_COLORS[cityName] || `rgb(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)})`;
    };

    const createChart = () => {
      if (!chartCanvas.value || !props.data) return;

      const ctx = chartCanvas.value.getContext('2d');
      
      // Build datasets
      const datasets = [];
      
      // Add city datasets
      if (props.data.cities) {
        for (const [cityName, temperatures] of Object.entries(props.data.cities)) {
          datasets.push({
            label: cityName,
            data: temperatures,
            borderColor: getCityColor(cityName),
            backgroundColor: getCityColor(cityName),
            tension: 0.3,
            pointRadius: 3
          });
        }
      } else if (props.data.temperatures) {
        // Single city data
        datasets.push({
          label: props.data.city,
          data: props.data.temperatures,
          borderColor: getCityColor(props.data.city),
          backgroundColor: getCityColor(props.data.city),
          tension: 0.3,
          pointRadius: 3
        });
      }
      
      // Add average dataset if it exists
      if (props.data.average) {
        datasets.push({
          label: 'Average',
          data: props.data.average,
          borderColor: CITY_COLORS.Average,
          backgroundColor: CITY_COLORS.Average,
          borderWidth: 3,
          tension: 0.3,
          pointRadius: 4
        });
      }

      // Create chart
      chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: props.data.months,
          datasets
        },
        options: {
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: props.title,
              font: {
                size: 16
              }
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const value = context.parsed.y;
                  return `${context.dataset.label}: ${value !== null ? value.toFixed(1) + '°C' : 'No data'}`;
                }
              }
            }
          },
          scales: {
            y: {
              title: {
                display: true,
                text: 'Temperature (°C)'
              }
            },
            x: {
              title: {
                display: true,
                text: 'Month'
              }
            }
          }
        }
      });
    };

    onMounted(() => {
      createChart();
    });

    watch(() => props.data, () => {
      if (chart) {
        chart.destroy();
      }
      createChart();
    }, { deep: true });

    return {
      chartCanvas
    };
  }
});
</script>

<style scoped>
.chart-container {
  position: relative;
  margin: auto;
}
</style> 