/**
 * Financial Chart Component
 * Comprehensive charting component for financial data visualization
 */
import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { TimeSeriesData, ComparisonChartData, ChartDataPoint } from '@/types/financial';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface FinancialChartProps {
  type: 'line' | 'bar' | 'doughnut';
  title: string;
  data: TimeSeriesData[] | ComparisonChartData[] | ChartDataPoint[];
  height?: number;
  showLegend?: boolean;
  showGrid?: boolean;
  currency?: boolean;
  percentage?: boolean;
  colors?: string[];
}

export function FinancialChart({
  type,
  title,
  data,
  height = 400,
  showLegend = true,
  showGrid = true,
  currency = false,
  percentage = false,
  colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'],
}: FinancialChartProps) {
  
  const formatValue = (value: number) => {
    if (currency) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(value);
    }
    
    if (percentage) {
      return `${(value * 100).toFixed(2)}%`;
    }
    
    // Format large numbers
    if (Math.abs(value) >= 1e9) {
      return `${(value / 1e9).toFixed(2)}B`;
    }
    if (Math.abs(value) >= 1e6) {
      return `${(value / 1e6).toFixed(2)}M`;
    }
    if (Math.abs(value) >= 1e3) {
      return `${(value / 1e3).toFixed(2)}K`;
    }
    
    return value.toFixed(2);
  };

  const getChartData = () => {
    if (type === 'line' && isTimeSeriesData(data)) {
      return {
        labels: data.map(d => new Date(d.date).toLocaleDateString()),
        datasets: [
          {
            label: title,
            data: data.map(d => d.value),
            borderColor: colors[0],
            backgroundColor: `${colors[0]}20`,
            borderWidth: 2,
            fill: true,
            tension: 0.4,
          },
        ],
      };
    }
    
    if (type === 'bar' && isComparisonData(data)) {
      return {
        labels: data.map(d => d.category),
        datasets: [
          {
            label: 'Company',
            data: data.map(d => d.company_value),
            backgroundColor: colors[0],
            borderColor: colors[0],
            borderWidth: 1,
          },
          {
            label: 'Peer Average',
            data: data.map(d => d.peer_average),
            backgroundColor: colors[1],
            borderColor: colors[1],
            borderWidth: 1,
          },
          ...(data.some(d => d.industry_average !== undefined) ? [{
            label: 'Industry Average',
            data: data.map(d => d.industry_average || 0),
            backgroundColor: colors[2],
            borderColor: colors[2],
            borderWidth: 1,
          }] : []),
        ],
      };
    }
    
    if (type === 'doughnut' && isChartDataPoint(data)) {
      return {
        labels: data.map(d => d.label || d.x),
        datasets: [
          {
            data: data.map(d => d.y),
            backgroundColor: colors.slice(0, data.length),
            borderColor: colors.slice(0, data.length),
            borderWidth: 2,
          },
        ],
      };
    }
    
    return { labels: [], datasets: [] };
  };

  const getChartOptions = () => {
    const baseOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: showLegend,
          position: 'top' as const,
        },
        title: {
          display: true,
          text: title,
          font: {
            size: 16,
            weight: 'bold' as const,
          },
        },
        tooltip: {
          callbacks: {
            label: (context: any) => {
              const label = context.dataset.label || '';
              const value = formatValue(context.parsed.y || context.parsed);
              return `${label}: ${value}`;
            },
          },
        },
      },
    };

    if (type === 'line' || type === 'bar') {
      return {
        ...baseOptions,
        scales: {
          x: {
            grid: {
              display: showGrid,
            },
          },
          y: {
            grid: {
              display: showGrid,
            },
            ticks: {
              callback: (value: any) => formatValue(value),
            },
          },
        },
      };
    }

    return baseOptions;
  };

  const chartData = getChartData();
  const chartOptions = getChartOptions();

  const renderChart = () => {
    switch (type) {
      case 'line':
        return <Line data={chartData} options={chartOptions} />;
      case 'bar':
        return <Bar data={chartData} options={chartOptions} />;
      case 'doughnut':
        return <Doughnut data={chartData} options={chartOptions} />;
      default:
        return null;
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border">
      <div style={{ height: `${height}px` }}>
        {renderChart()}
      </div>
    </div>
  );
}

// Type guards
function isTimeSeriesData(data: any[]): data is TimeSeriesData[] {
  return data.length > 0 && 'date' in data[0] && 'value' in data[0];
}

function isComparisonData(data: any[]): data is ComparisonChartData[] {
  return data.length > 0 && 'category' in data[0] && 'company_value' in data[0];
}

function isChartDataPoint(data: any[]): data is ChartDataPoint[] {
  return data.length > 0 && 'x' in data[0] && 'y' in data[0];
}

export default FinancialChart;